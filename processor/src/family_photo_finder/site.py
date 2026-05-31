"""Generates the static site payload (people.json)."""

from __future__ import annotations

import json
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

from .config import Config
from .logging_utils import get_logger
from .models import Cluster, FaceDetection, PhotoRecord

logger = get_logger(__name__)


class SiteBuilder:
    def __init__(self, config: Config) -> None:
        self.config = config

    def build(
        self,
        photos: list[PhotoRecord],
        faces: list[FaceDetection],
        clusters: list[Cluster],
        labels: dict[str, str],
        site_data_dir: Path,
    ) -> Path:
        site_data_dir.mkdir(parents=True, exist_ok=True)

        photos_by_id = {p.photo_id: p for p in photos}
        faces_by_photo: dict[str, list[FaceDetection]] = defaultdict(list)
        for face in faces:
            if face.cluster_id is not None:
                faces_by_photo[face.photo_id].append(face)

        people = []
        for index, cluster in enumerate(clusters):
            label = (labels.get(cluster.cluster_id) or "").strip()
            if not label:
                label = f"Person {index + 1}"

            cluster_photo_ids = sorted(cluster.photo_ids)
            cluster_photos = []
            for photo_id in cluster_photo_ids:
                record = photos_by_id.get(photo_id)
                if record is None:
                    continue
                cluster_photos.append(
                    {
                        "thumbnail": f"data/photo-thumbnails/{record.thumbnail_name}",
                        "driveUrl": record.drive_url,
                    }
                )

            people.append(
                {
                    "id": cluster.cluster_id,
                    "name": label,
                    "faceThumbnail": f"data/faces/{cluster.cluster_id}.jpg",
                    "photoCount": len(cluster_photos),
                    "photos": cluster_photos,
                }
            )

        people.sort(key=lambda p: (-p["photoCount"], p["name"].lower()))

        payload = {
            "eventTitle": self.config.event_title,
            "generatedAt": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "people": people,
        }

        target = site_data_dir / "people.json"
        with target.open("w", encoding="utf-8") as fh:
            json.dump(payload, fh, indent=2)
        logger.info(
            "Wrote %d people to %s (event: %s).",
            len(people),
            target,
            self.config.event_title,
        )
        return target
