"""Configuration loading and project paths."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml


@dataclass(frozen=True)
class Paths:
    """Filesystem layout for the processor + output tree."""

    processor_root: Path
    project_root: Path
    cache_dir: Path
    state_dir: Path
    output_dir: Path
    faces_dir: Path
    thumbs_dir: Path
    review_dir: Path
    site_data_dir: Path
    website_dir: Path
    website_public_data_dir: Path

    @classmethod
    def from_processor_root(cls, processor_root: Path) -> "Paths":
        processor_root = processor_root.resolve()
        project_root = processor_root.parent
        output_dir = project_root / "output"
        website_dir = project_root / "website"
        return cls(
            processor_root=processor_root,
            project_root=project_root,
            cache_dir=processor_root / "cache",
            state_dir=processor_root / "state",
            output_dir=output_dir,
            faces_dir=output_dir / "faces",
            thumbs_dir=output_dir / "photo-thumbnails",
            review_dir=output_dir / "review",
            site_data_dir=output_dir / "website-data",
            website_dir=website_dir,
            website_public_data_dir=website_dir / "public" / "data",
        )

    def ensure(self) -> None:
        for directory in (
            self.cache_dir,
            self.state_dir,
            self.output_dir,
            self.faces_dir,
            self.thumbs_dir,
            self.review_dir,
            self.site_data_dir,
        ):
            directory.mkdir(parents=True, exist_ok=True)


@dataclass(frozen=True)
class Config:
    """Runtime configuration for the pipeline.

    Values are loaded from ``processor/config.yaml`` with sensible defaults so
    a missing key never crashes the pipeline.
    """

    event_title: str = "Family Function"
    google_drive_folder: str = ""
    thumbnail_size: int = 400
    face_thumbnail_size: int = 256
    dbscan_eps: float = 0.45
    dbscan_min_samples: int = 2
    min_face_size: int = 80
    detection_confidence: float = 0.5
    download_concurrency: int = 4
    raw: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def load(cls, config_path: Path) -> "Config":
        if not config_path.exists():
            return cls(raw={})
        with config_path.open("r", encoding="utf-8") as fh:
            data = yaml.safe_load(fh) or {}
        if not isinstance(data, dict):
            raise ValueError(
                f"{config_path} must contain a YAML mapping at the top level."
            )
        return cls(
            event_title=str(data.get("event_title", "Family Function")),
            google_drive_folder=str(data.get("google_drive_folder", "")),
            thumbnail_size=int(data.get("thumbnail_size", 400)),
            face_thumbnail_size=int(data.get("face_thumbnail_size", 256)),
            dbscan_eps=float(data.get("dbscan_eps", 0.45)),
            dbscan_min_samples=int(data.get("dbscan_min_samples", 2)),
            min_face_size=int(data.get("min_face_size", 80)),
            detection_confidence=float(data.get("detection_confidence", 0.5)),
            download_concurrency=int(data.get("download_concurrency", 4)),
            raw=data,
        )


def default_processor_root() -> Path:
    """Return the absolute path of the ``processor`` directory."""

    return Path(__file__).resolve().parents[2]
