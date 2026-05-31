"""Temporary local cache for original Drive downloads."""

from __future__ import annotations

import shutil
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from tqdm import tqdm

from .drive import DriveClient
from .logging_utils import get_logger
from .models import DrivePhoto

logger = get_logger(__name__)


@dataclass
class CachedPhoto:
    drive_photo: DrivePhoto
    path: Path


class ImageCache:
    """Manages ``processor/cache/`` — a strictly temporary working directory.

    Originals are downloaded here, used for face detection and thumbnailing,
    and then deleted by :meth:`cleanup`.
    """

    def __init__(self, cache_dir: Path) -> None:
        self.cache_dir = cache_dir
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self._purge_stale_partials()

    def _purge_stale_partials(self) -> None:
        for part in self.cache_dir.glob("*.part"):
            try:
                part.unlink()
            except OSError:
                pass

    def download_all(
        self,
        client: DriveClient,
        photos: Iterable[DrivePhoto],
        concurrency: int = 4,
    ) -> list[CachedPhoto]:
        """Download every photo in ``photos`` to the cache directory.

        ``concurrency`` defaults to a conservative value because Google's edge
        is happiest with a small handful of parallel TLS streams per client.
        """

        targets = list(photos)
        if not targets:
            return []

        results: list[CachedPhoto] = []
        failed = 0

        def _task(photo: DrivePhoto) -> CachedPhoto | None:
            destination = self.cache_dir / f"{photo.drive_id}_{_safe_name(photo.name)}"
            if destination.exists():
                size = destination.stat().st_size
                # If we know the expected size, only trust the cached file if
                # it matches exactly. Catches truncated downloads from prior
                # crashes that wrote straight to the destination.
                if size > 0 and (photo.size is None or size == photo.size):
                    return CachedPhoto(photo, destination)
                destination.unlink(missing_ok=True)
            try:
                client.download_to(photo.drive_id, destination)
            except Exception as exc:  # noqa: BLE001 - surface and continue
                logger.warning(
                    "Download failed for %s (%s): %s",
                    photo.name,
                    photo.drive_id,
                    exc,
                )
                if destination.exists():
                    destination.unlink(missing_ok=True)
                return None
            return CachedPhoto(photo, destination)

        workers = max(1, min(concurrency, 16))
        with ThreadPoolExecutor(max_workers=workers) as pool:
            futures = {pool.submit(_task, photo): photo for photo in targets}
            with tqdm(total=len(futures), desc="Download", unit="img") as bar:
                for future in as_completed(futures):
                    cached = future.result()
                    if cached is not None:
                        results.append(cached)
                    else:
                        failed += 1
                    bar.update(1)
        if failed:
            logger.warning(
                "%d / %d photos failed to download after retries.",
                failed,
                len(targets),
            )
        return results

    def cleanup(self) -> None:
        """Delete the cache directory completely. Originals are never retained."""

        if self.cache_dir.exists():
            shutil.rmtree(self.cache_dir)
            logger.info("Removed cache directory %s", self.cache_dir)


def _safe_name(name: str) -> str:
    keep = "._-"
    return "".join(c if c.isalnum() or c in keep else "_" for c in name)[:120]
