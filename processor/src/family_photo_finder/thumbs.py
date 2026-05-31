"""Face and photo thumbnail generation."""

from __future__ import annotations

from pathlib import Path

from PIL import Image
from tqdm import tqdm

from .cache import CachedPhoto
from .config import Config
from .imaging import load_pil
from .logging_utils import get_logger
from .models import Cluster, FaceDetection, PhotoRecord

logger = get_logger(__name__)


class Thumbnailer:
    """Generates both photo thumbnails and per-cluster face thumbnails."""

    def __init__(self, config: Config) -> None:
        self.config = config

    def write_photo_thumbnails(
        self,
        cached_photos: list[CachedPhoto],
        photos: list[PhotoRecord],
        thumbs_dir: Path,
    ) -> None:
        """Write a web-friendly thumbnail for every photo record.

        Photos are matched to their cached file by Drive id. Photos with no
        cached file (i.e. download failed) are skipped silently.
        """

        thumbs_dir.mkdir(parents=True, exist_ok=True)
        cached_by_drive_id = {c.drive_photo.drive_id: c for c in cached_photos}

        for record in tqdm(photos, desc="Photo thumbs", unit="img"):
            cached = cached_by_drive_id.get(record.drive_id)
            if cached is None:
                continue
            destination = thumbs_dir / record.thumbnail_name
            try:
                self._write_photo_thumb(cached.path, destination)
            except Exception as exc:  # noqa: BLE001
                logger.warning("Failed to write thumb for %s: %s", cached.path, exc)

    def _write_photo_thumb(self, source: Path, destination: Path) -> None:
        image = load_pil(source)
        target_width = self.config.thumbnail_size
        if image.width > target_width:
            ratio = target_width / image.width
            new_size = (target_width, max(1, int(round(image.height * ratio))))
            image = image.resize(new_size, Image.LANCZOS)
        image.save(destination, format="JPEG", quality=82, optimize=True, progressive=True)

    def write_face_thumbnails(
        self,
        cached_photos: list[CachedPhoto],
        photos: list[PhotoRecord],
        faces: list[FaceDetection],
        clusters: list[Cluster],
        faces_dir: Path,
        samples_dir: Path | None = None,
        samples_per_cluster: int = 6,
    ) -> None:
        """Write one face thumbnail per cluster plus optional review samples.

        The representative face is written as ``<faces_dir>/<cluster_id>.jpg``.
        If ``samples_dir`` is provided, up to ``samples_per_cluster`` additional
        face crops are written to ``<samples_dir>/<cluster_id>/N.jpg`` for use
        by the review UI.
        """

        faces_dir.mkdir(parents=True, exist_ok=True)
        if samples_dir is not None:
            samples_dir.mkdir(parents=True, exist_ok=True)

        photos_by_id = {p.photo_id: p for p in photos}
        cached_by_drive_id = {c.drive_photo.drive_id: c for c in cached_photos}
        faces_by_id = {f.face_id: f for f in faces}

        size = self.config.face_thumbnail_size

        faces_by_cluster: dict[str, list[FaceDetection]] = {}
        for face in faces:
            if face.cluster_id is not None:
                faces_by_cluster.setdefault(face.cluster_id, []).append(face)

        for cluster in tqdm(clusters, desc="Face thumbs", unit="cluster"):
            face = faces_by_id.get(cluster.representative_face_id)
            if face is None:
                continue
            photo = photos_by_id.get(face.photo_id)
            if photo is None:
                continue
            cached = cached_by_drive_id.get(photo.drive_id)
            if cached is None:
                continue
            destination = faces_dir / f"{cluster.cluster_id}.jpg"
            try:
                self._write_face_thumb(cached.path, face, size, destination)
            except Exception as exc:  # noqa: BLE001
                logger.warning(
                    "Failed face thumb for %s (%s): %s", cluster.cluster_id, cached.path, exc
                )

            if samples_dir is None:
                continue

            members = sorted(
                faces_by_cluster.get(cluster.cluster_id, []),
                key=lambda f: -f.confidence,
            )[:samples_per_cluster]
            cluster_dir = samples_dir / cluster.cluster_id
            cluster_dir.mkdir(parents=True, exist_ok=True)
            for i, sample in enumerate(members):
                sample_photo = photos_by_id.get(sample.photo_id)
                if sample_photo is None:
                    continue
                sample_cached = cached_by_drive_id.get(sample_photo.drive_id)
                if sample_cached is None:
                    continue
                sample_dest = cluster_dir / f"{i}.jpg"
                try:
                    self._write_face_thumb(sample_cached.path, sample, size, sample_dest)
                except Exception as exc:  # noqa: BLE001
                    logger.warning(
                        "Failed sample face %s/%d: %s", cluster.cluster_id, i, exc
                    )

    def _write_face_thumb(
        self,
        source: Path,
        face: FaceDetection,
        size: int,
        destination: Path,
    ) -> None:
        image = load_pil(source)
        x1, y1, x2, y2 = face.bbox
        face_w = x2 - x1
        face_h = y2 - y1
        cx = x1 + face_w / 2
        cy = y1 + face_h / 2

        side = int(round(max(face_w, face_h) * 1.6))
        side = max(side, 1)

        left = int(round(cx - side / 2))
        top = int(round(cy - side / 2))
        right = left + side
        bottom = top + side

        img_w, img_h = image.size
        pad_left = max(0, -left)
        pad_top = max(0, -top)
        pad_right = max(0, right - img_w)
        pad_bottom = max(0, bottom - img_h)

        if pad_left or pad_top or pad_right or pad_bottom:
            padded = Image.new(
                "RGB",
                (img_w + pad_left + pad_right, img_h + pad_top + pad_bottom),
                (32, 32, 32),
            )
            padded.paste(image, (pad_left, pad_top))
            image = padded
            left += pad_left
            top += pad_top
            right += pad_left
            bottom += pad_top

        cropped = image.crop((left, top, right, bottom))
        cropped = cropped.resize((size, size), Image.LANCZOS)
        cropped.save(destination, format="JPEG", quality=88, optimize=True, progressive=True)
