"""Face detection + embedding using InsightFace."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

import numpy as np
from tqdm import tqdm

from .cache import CachedPhoto
from .config import Config
from .imaging import load_bgr
from .logging_utils import get_logger
from .models import FaceDetection, PhotoRecord

logger = get_logger(__name__)


@dataclass
class DetectionResult:
    photos: list[PhotoRecord]
    faces: list[FaceDetection]


class FaceDetector:
    """Wraps InsightFace's ``FaceAnalysis`` with our project conventions.

    The model is loaded lazily so importing the module is cheap.
    """

    def __init__(self, config: Config) -> None:
        self.config = config
        self._analysis = None

    def _load_model(self):
        if self._analysis is None:
            from insightface.app import FaceAnalysis

            logger.info("Loading InsightFace model (buffalo_l)...")
            self._analysis = FaceAnalysis(
                name="buffalo_l",
                allowed_modules=["detection", "recognition"],
            )
            self._analysis.prepare(ctx_id=0, det_size=(640, 640))
        return self._analysis

    def detect(self, cached_photos: Iterable[CachedPhoto]) -> DetectionResult:
        """Detect faces in every cached photo and build PhotoRecord + FaceDetection rows."""

        analysis = self._load_model()
        photos: list[PhotoRecord] = []
        faces: list[FaceDetection] = []
        cached_list = list(cached_photos)

        for index, cached in enumerate(tqdm(cached_list, desc="Detect", unit="img")):
            photo_id = f"photo_{index + 1:06d}"
            try:
                image_bgr = load_bgr(cached.path)
            except Exception as exc:  # noqa: BLE001
                logger.warning("Skipping unreadable image %s: %s", cached.path, exc)
                continue

            height, width = image_bgr.shape[:2]
            thumbnail_name = f"thumb_{index + 1:06d}.jpg"

            record = PhotoRecord(
                photo_id=photo_id,
                drive_id=cached.drive_photo.drive_id,
                original_name=cached.drive_photo.name,
                thumbnail_name=thumbnail_name,
                width=width,
                height=height,
            )
            photos.append(record)

            try:
                detections = analysis.get(image_bgr)
            except Exception as exc:  # noqa: BLE001
                logger.warning("Detection failed on %s: %s", cached.path, exc)
                continue

            for face_index, face in enumerate(detections):
                bbox = self._sanitise_bbox(face.bbox, width, height)
                if bbox is None:
                    continue
                x1, y1, x2, y2 = bbox
                face_w = x2 - x1
                face_h = y2 - y1
                if face_w < self.config.min_face_size or face_h < self.config.min_face_size:
                    continue

                det_score = float(getattr(face, "det_score", 1.0))
                if det_score < self.config.detection_confidence:
                    continue

                embedding = getattr(face, "normed_embedding", None)
                if embedding is None:
                    embedding = getattr(face, "embedding", None)
                if embedding is None:
                    continue
                embedding_np = np.asarray(embedding, dtype=np.float32)
                norm = float(np.linalg.norm(embedding_np))
                if norm > 0:
                    embedding_np = embedding_np / norm

                face_id = f"{photo_id}_face_{face_index:02d}"
                faces.append(
                    FaceDetection(
                        face_id=face_id,
                        photo_id=photo_id,
                        bbox=(x1, y1, x2, y2),
                        confidence=det_score,
                        embedding=embedding_np.tolist(),
                        detector_score=det_score,
                    )
                )

        logger.info(
            "Detected %d faces across %d photos (min size %dpx, conf >= %.2f).",
            len(faces),
            len(photos),
            self.config.min_face_size,
            self.config.detection_confidence,
        )
        return DetectionResult(photos=photos, faces=faces)

    @staticmethod
    def _sanitise_bbox(
        bbox: np.ndarray | list[float], width: int, height: int
    ) -> tuple[int, int, int, int] | None:
        if bbox is None:
            return None
        x1, y1, x2, y2 = [float(v) for v in bbox]
        x1 = max(0, int(round(x1)))
        y1 = max(0, int(round(y1)))
        x2 = min(width, int(round(x2)))
        y2 = min(height, int(round(y2)))
        if x2 <= x1 or y2 <= y1:
            return None
        return x1, y1, x2, y2


def load_image_for_face(path: Path) -> np.ndarray:
    """Reload an image (BGR) for face thumbnail cropping."""

    return load_bgr(path)
