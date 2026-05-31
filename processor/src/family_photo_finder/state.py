"""Persisted pipeline state — JSON files in processor/state/."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .models import Cluster, FaceDetection, PhotoRecord


def _atomic_write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    with tmp.open("w", encoding="utf-8") as fh:
        json.dump(payload, fh, indent=2)
    tmp.replace(path)


def _read_json(path: Path, default: Any) -> Any:
    if not path.exists():
        return default
    with path.open("r", encoding="utf-8") as fh:
        return json.load(fh)


class PipelineState:
    """Read/write the JSON files we persist between pipeline stages."""

    def __init__(self, state_dir: Path) -> None:
        self.state_dir = state_dir
        self.photos_path = state_dir / "photos.json"
        self.faces_path = state_dir / "faces.json"
        self.clusters_path = state_dir / "clusters.json"
        self.labels_path = state_dir / "labels.json"

    def save_photos(self, photos: list[PhotoRecord]) -> None:
        _atomic_write_json(
            self.photos_path,
            [
                {
                    "photo_id": p.photo_id,
                    "drive_id": p.drive_id,
                    "original_name": p.original_name,
                    "thumbnail_name": p.thumbnail_name,
                    "width": p.width,
                    "height": p.height,
                }
                for p in photos
            ],
        )

    def load_photos(self) -> list[PhotoRecord]:
        rows = _read_json(self.photos_path, [])
        return [PhotoRecord(**row) for row in rows]

    def save_faces(self, faces: list[FaceDetection]) -> None:
        _atomic_write_json(self.faces_path, [f.to_dict() for f in faces])

    def load_faces(self) -> list[FaceDetection]:
        rows = _read_json(self.faces_path, [])
        result: list[FaceDetection] = []
        for row in rows:
            row = dict(row)
            row["bbox"] = tuple(row["bbox"])
            result.append(FaceDetection(**row))
        return result

    def save_clusters(self, clusters: list[Cluster]) -> None:
        _atomic_write_json(self.clusters_path, [c.to_dict() for c in clusters])

    def load_clusters(self) -> list[Cluster]:
        rows = _read_json(self.clusters_path, [])
        return [Cluster(**row) for row in rows]

    def save_labels(self, labels: dict[str, str]) -> None:
        _atomic_write_json(self.labels_path, labels)

    def load_labels(self) -> dict[str, str]:
        return dict(_read_json(self.labels_path, {}))
