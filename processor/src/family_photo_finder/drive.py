"""Google Drive integration.

Uses the official ``google-api-python-client`` SDK. Authenticates via a Desktop
OAuth client at ``processor/credentials.json`` and persists a refresh token to
``processor/token.json``.
"""

from __future__ import annotations

import random
import re
import socket
import ssl
import threading
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Iterator

import requests
from google.auth.transport.requests import AuthorizedSession, Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from .logging_utils import get_logger
from .models import SUPPORTED_EXTENSIONS, SUPPORTED_MIME_TYPES, DrivePhoto

logger = get_logger(__name__)

SCOPES = ["https://www.googleapis.com/auth/drive.readonly"]
DOWNLOAD_URL = "https://www.googleapis.com/drive/v3/files/{file_id}"
DOWNLOAD_CHUNK_SIZE = 1024 * 1024  # 1 MiB
DOWNLOAD_MAX_ATTEMPTS = 6
DOWNLOAD_CONNECT_TIMEOUT = 20
DOWNLOAD_READ_TIMEOUT = 180

# Errors that almost always indicate a transient network/SSL hiccup worth
# retrying with exponential backoff.
TRANSIENT_NETWORK_ERRORS: tuple[type[BaseException], ...] = (
    requests.exceptions.ConnectionError,
    requests.exceptions.ChunkedEncodingError,
    requests.exceptions.ReadTimeout,
    requests.exceptions.Timeout,
    ssl.SSLError,
    socket.timeout,
    ConnectionError,
    OSError,
)


class MissingCredentialsError(RuntimeError):
    """Raised when ``processor/credentials.json`` is missing.

    Carries the expected path so the CLI can render a nice setup banner.
    """

    def __init__(self, credentials_path: Path) -> None:
        super().__init__(f"Google OAuth client file not found at {credentials_path}.")
        self.credentials_path = credentials_path

FOLDER_URL_PATTERNS = (
    re.compile(r"/folders/([a-zA-Z0-9_-]+)"),
    re.compile(r"[?&]id=([a-zA-Z0-9_-]+)"),
)


def extract_folder_id(folder_url_or_id: str) -> str:
    """Extract a folder id from a Drive URL, or return the input if it already
    looks like an id."""

    candidate = folder_url_or_id.strip()
    if not candidate:
        raise ValueError("Drive folder URL/ID is empty.")

    for pattern in FOLDER_URL_PATTERNS:
        match = pattern.search(candidate)
        if match:
            return match.group(1)

    if re.fullmatch(r"[a-zA-Z0-9_-]{10,}", candidate):
        return candidate

    raise ValueError(f"Could not extract a Drive folder ID from: {folder_url_or_id!r}")


@dataclass
class DriveCredentialPaths:
    credentials: Path
    token: Path


class DriveClient:
    """Thin wrapper around the Drive v3 API focused on enumerating images
    inside a folder and streaming them to disk.

    Listing uses the official ``googleapiclient`` service (single-threaded).
    Downloading uses one ``AuthorizedSession`` per worker thread, because
    ``httplib2`` is **not** thread-safe — sharing one service across threads
    produces SSL record-layer failures and corrupted state.
    """

    def __init__(self, credential_paths: DriveCredentialPaths) -> None:
        self._paths = credential_paths
        self._service = None
        self._creds: Credentials | None = None
        self._creds_lock = threading.Lock()
        self._local = threading.local()

    def _ensure_service(self):
        if self._service is None:
            creds = self._ensure_credentials()
            self._service = build("drive", "v3", credentials=creds, cache_discovery=False)
        return self._service

    def _ensure_credentials(self) -> Credentials:
        with self._creds_lock:
            if self._creds is None:
                self._creds = self._load_credentials()
            return self._creds

    def _get_session(self) -> AuthorizedSession:
        session = getattr(self._local, "session", None)
        if session is None:
            creds = self._ensure_credentials()
            session = AuthorizedSession(creds)
            session.headers.update({"User-Agent": "family-photo-finder/0.1"})
            self._local.session = session
        return session

    def _load_credentials(self) -> Credentials:
        token_path = self._paths.token
        creds: Credentials | None = None

        if token_path.exists():
            creds = Credentials.from_authorized_user_file(str(token_path), SCOPES)

        if creds and creds.valid:
            return creds

        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
            token_path.write_text(creds.to_json(), encoding="utf-8")
            return creds

        if not self._paths.credentials.exists():
            raise MissingCredentialsError(self._paths.credentials)

        flow = InstalledAppFlow.from_client_secrets_file(
            str(self._paths.credentials), SCOPES
        )
        creds = flow.run_local_server(port=0)
        token_path.write_text(creds.to_json(), encoding="utf-8")
        return creds

    def list_images(self, folder_id: str) -> Iterator[DrivePhoto]:
        """Recursively yield image files contained in ``folder_id``.

        Walks shortcut and subfolders. Unsupported file types are skipped.
        """

        service = self._ensure_service()
        seen_folders: set[str] = set()
        queue: list[str] = [folder_id]

        while queue:
            current = queue.pop(0)
            if current in seen_folders:
                continue
            seen_folders.add(current)

            for entry in self._iter_children(service, current):
                mime = entry.get("mimeType", "")
                if mime == "application/vnd.google-apps.folder":
                    queue.append(entry["id"])
                    continue
                if mime == "application/vnd.google-apps.shortcut":
                    details = entry.get("shortcutDetails", {})
                    target_id = details.get("targetId")
                    target_mime = details.get("targetMimeType", "")
                    if target_id and target_mime == "application/vnd.google-apps.folder":
                        queue.append(target_id)
                        continue
                    if target_id and self._is_supported(target_mime, entry.get("name", "")):
                        yield DrivePhoto(
                            drive_id=target_id,
                            name=entry.get("name", target_id),
                            mime_type=target_mime,
                            size=int(entry["size"]) if entry.get("size") else None,
                            md5=entry.get("md5Checksum"),
                            modified_time=entry.get("modifiedTime"),
                        )
                    continue

                name = entry.get("name", "")
                if not self._is_supported(mime, name):
                    continue

                yield DrivePhoto(
                    drive_id=entry["id"],
                    name=name,
                    mime_type=mime,
                    size=int(entry["size"]) if entry.get("size") else None,
                    md5=entry.get("md5Checksum"),
                    modified_time=entry.get("modifiedTime"),
                )

    def _iter_children(self, service, folder_id: str) -> Iterable[dict]:
        page_token: str | None = None
        while True:
            try:
                response = (
                    service.files()
                    .list(
                        q=f"'{folder_id}' in parents and trashed = false",
                        fields=(
                            "nextPageToken, files(id, name, mimeType, size, md5Checksum, "
                            "modifiedTime, shortcutDetails)"
                        ),
                        pageSize=1000,
                        pageToken=page_token,
                        supportsAllDrives=True,
                        includeItemsFromAllDrives=True,
                    )
                    .execute()
                )
            except HttpError as exc:
                logger.warning("Drive list failed for %s: %s", folder_id, exc)
                return

            for entry in response.get("files", []):
                yield entry

            page_token = response.get("nextPageToken")
            if not page_token:
                return

    @staticmethod
    def _is_supported(mime_type: str, name: str) -> bool:
        if mime_type in SUPPORTED_MIME_TYPES:
            return True
        suffix = Path(name).suffix.lower()
        return suffix in SUPPORTED_EXTENSIONS

    def download_to(self, drive_id: str, destination: Path) -> Path:
        """Stream a file from Drive into ``destination`` with retries.

        Uses a per-thread :class:`AuthorizedSession` (which wraps
        ``requests.Session``) so that concurrent downloads each own their
        TLS connection. Writes to ``<destination>.part`` and atomically
        renames on success, so a killed process never leaves a corrupt file
        behind that we'd treat as already-downloaded next time.
        """

        destination.parent.mkdir(parents=True, exist_ok=True)
        part = destination.with_suffix(destination.suffix + ".part")
        url = DOWNLOAD_URL.format(file_id=drive_id)
        params = {"alt": "media", "supportsAllDrives": "true"}

        last_exc: Exception | None = None
        for attempt in range(1, DOWNLOAD_MAX_ATTEMPTS + 1):
            session = self._get_session()
            try:
                with session.get(
                    url,
                    params=params,
                    stream=True,
                    timeout=(DOWNLOAD_CONNECT_TIMEOUT, DOWNLOAD_READ_TIMEOUT),
                ) as response:
                    if response.status_code in (401, 403):
                        # Refresh credentials once on auth failure, then retry.
                        response.close()
                        self._refresh_session()
                        raise requests.exceptions.ConnectionError(
                            f"Auth refresh required (HTTP {response.status_code})"
                        )
                    response.raise_for_status()
                    with part.open("wb") as fh:
                        for chunk in response.iter_content(chunk_size=DOWNLOAD_CHUNK_SIZE):
                            if chunk:
                                fh.write(chunk)
                part.replace(destination)
                return destination
            except TRANSIENT_NETWORK_ERRORS as exc:
                last_exc = exc
                part.unlink(missing_ok=True)
                if attempt >= DOWNLOAD_MAX_ATTEMPTS:
                    break
                sleep = min(2 ** (attempt - 1), 30) + random.uniform(0, 0.5)
                logger.debug(
                    "Transient download error for %s (attempt %d/%d): %s. "
                    "Sleeping %.1fs.",
                    drive_id,
                    attempt,
                    DOWNLOAD_MAX_ATTEMPTS,
                    exc,
                    sleep,
                )
                time.sleep(sleep)
                # Force a fresh session on the next attempt to drop any
                # poisoned connection pool entries.
                self._drop_thread_session()
            except requests.exceptions.HTTPError as exc:
                status = exc.response.status_code if exc.response is not None else None
                part.unlink(missing_ok=True)
                if status in (429, 500, 502, 503, 504) and attempt < DOWNLOAD_MAX_ATTEMPTS:
                    last_exc = exc
                    sleep = min(2 ** (attempt - 1), 30) + random.uniform(0, 0.5)
                    logger.debug(
                        "Retrying %s after HTTP %s (attempt %d/%d, sleeping %.1fs).",
                        drive_id,
                        status,
                        attempt,
                        DOWNLOAD_MAX_ATTEMPTS,
                        sleep,
                    )
                    time.sleep(sleep)
                    continue
                raise

        assert last_exc is not None
        raise last_exc

    def _drop_thread_session(self) -> None:
        session = getattr(self._local, "session", None)
        if session is not None:
            try:
                session.close()
            except Exception:  # noqa: BLE001
                pass
            self._local.session = None

    def _refresh_session(self) -> None:
        """Force a credentials refresh and rebuild this thread's session."""

        with self._creds_lock:
            if self._creds is not None:
                try:
                    self._creds.refresh(Request())
                    self._paths.token.write_text(self._creds.to_json(), encoding="utf-8")
                except Exception as exc:  # noqa: BLE001
                    logger.debug("Credential refresh failed: %s", exc)
        self._drop_thread_session()
