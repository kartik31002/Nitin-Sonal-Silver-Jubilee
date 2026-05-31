"""Dataclasses representing pipeline records."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


SUPPORTED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".heic", ".webp"}
SUPPORTED_MIME_TYPES = {
    "image/jpeg",
    "image/png",
    "image/heic",
    "image/heif",
    "image/webp",
}


@dataclass
class DrivePhoto:
    """Metadata for a single Drive file we intend to download."""

    drive_id: str
    name: str
    mime_type: str
    size: int | None = None
    md5: str | None = None
    modified_time: str | None = None

    @property
    def drive_url(self) -> str:
        return f"https://drive.google.com/file/d/{self.drive_id}/view"


@dataclass
class PhotoRecord:
    """A photo that has been downloaded and assigned a stable local id."""

    photo_id: str
    drive_id: str
    original_name: str
    thumbnail_name: str
    width: int
    height: int

    @property
    def drive_url(self) -> str:
        return f"https://drive.google.com/file/d/{self.drive_id}/view"


@dataclass
class FaceDetection:
    """A single face detected in a photo.

    Embedding is stored as a list[float] so the record is JSON-serialisable.
    """

    face_id: str
    photo_id: str
    bbox: tuple[int, int, int, int]
    confidence: float
    embedding: list[float]
    detector_score: float = 0.0
    cluster_id: str | None = None

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["bbox"] = list(self.bbox)
        return data


@dataclass
class Cluster:
    """One unique person."""

    cluster_id: str
    representative_face_id: str
    photo_ids: list[str] = field(default_factory=list)
    face_count: int = 0

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
