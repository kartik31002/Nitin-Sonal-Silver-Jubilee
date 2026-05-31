"""High-level orchestration for the ``process`` command."""

from __future__ import annotations

from dataclasses import dataclass

from .cache import ImageCache
from .cluster import cluster_faces
from .config import Config, Paths
from .detect import FaceDetector
from .drive import DriveClient, DriveCredentialPaths, extract_folder_id
from .logging_utils import get_logger
from .review import Reviewer
from .state import PipelineState
from .thumbs import Thumbnailer

logger = get_logger(__name__)


@dataclass
class PipelineSummary:
    photo_count: int
    face_count: int
    cluster_count: int


def run_pipeline(
    *,
    config: Config,
    paths: Paths,
    folder_url: str,
    skip_cleanup: bool = False,
    concurrency: int | None = None,
) -> PipelineSummary:
    """Download from Drive, detect, cluster, generate thumbs, write review UI."""

    paths.ensure()
    folder_id = extract_folder_id(folder_url)
    logger.info("Drive folder ID resolved to %s", folder_id)

    credentials = DriveCredentialPaths(
        credentials=paths.processor_root / "credentials.json",
        token=paths.processor_root / "token.json",
    )
    client = DriveClient(credentials)

    logger.info("Listing photos in Drive folder...")
    drive_photos = list(client.list_images(folder_id))
    logger.info("Found %d supported images.", len(drive_photos))
    if not drive_photos:
        raise RuntimeError("No supported images found in the Drive folder.")

    effective_concurrency = concurrency if concurrency is not None else config.download_concurrency
    logger.info("Downloading with concurrency=%d.", effective_concurrency)
    cache = ImageCache(paths.cache_dir)
    cached = cache.download_all(
        client,
        drive_photos,
        concurrency=effective_concurrency,
    )
    if not cached:
        raise RuntimeError("All Drive downloads failed; aborting.")
    logger.info("Downloaded %d / %d images.", len(cached), len(drive_photos))

    detector = FaceDetector(config)
    detection = detector.detect(cached)
    photos = detection.photos
    faces = detection.faces

    faces, clusters = cluster_faces(faces, config)

    state = PipelineState(paths.state_dir)
    state.save_photos(photos)
    state.save_faces(faces)
    state.save_clusters(clusters)

    cluster_samples_dir = paths.output_dir / "cluster-samples"
    thumbnailer = Thumbnailer(config)
    thumbnailer.write_photo_thumbnails(cached, photos, paths.thumbs_dir)
    thumbnailer.write_face_thumbnails(
        cached_photos=cached,
        photos=photos,
        faces=faces,
        clusters=clusters,
        faces_dir=paths.faces_dir,
        samples_dir=cluster_samples_dir,
    )

    reviewer = Reviewer(paths.review_dir, paths.faces_dir)
    reviewer.write(
        clusters,
        faces,
        cluster_samples_dir=cluster_samples_dir,
        existing_labels=state.load_labels(),
    )

    if not skip_cleanup:
        cache.cleanup()
    else:
        logger.info("Skipping cache cleanup (--keep-cache).")

    return PipelineSummary(
        photo_count=len(photos),
        face_count=len(faces),
        cluster_count=len(clusters),
    )
