"""DBSCAN clustering over face embeddings."""

from __future__ import annotations

from collections import defaultdict
from typing import Iterable

import numpy as np
from sklearn.cluster import DBSCAN

from .config import Config
from .logging_utils import get_logger
from .models import Cluster, FaceDetection

logger = get_logger(__name__)


def cluster_faces(
    faces: list[FaceDetection],
    config: Config,
) -> tuple[list[FaceDetection], list[Cluster]]:
    """Cluster face embeddings with DBSCAN (cosine distance).

    Mutates the ``cluster_id`` field of each input face to either a
    ``cluster_XXXX`` id or ``None`` if the face was classified as noise.

    Returns the (possibly mutated) faces and the list of cluster summaries.
    """

    if not faces:
        return faces, []

    embeddings = np.asarray([f.embedding for f in faces], dtype=np.float32)
    if embeddings.ndim != 2 or embeddings.shape[0] == 0:
        return faces, []

    logger.info(
        "Running DBSCAN on %d embeddings (eps=%.3f, min_samples=%d)...",
        embeddings.shape[0],
        config.dbscan_eps,
        config.dbscan_min_samples,
    )

    model = DBSCAN(
        eps=config.dbscan_eps,
        min_samples=config.dbscan_min_samples,
        metric="cosine",
        n_jobs=-1,
    )
    labels = model.fit_predict(embeddings)

    raw_to_cluster_id = _assign_cluster_ids(labels)

    clusters_by_id: dict[str, list[FaceDetection]] = defaultdict(list)
    for face, raw in zip(faces, labels):
        cluster_id = raw_to_cluster_id.get(int(raw))
        face.cluster_id = cluster_id
        if cluster_id is not None:
            clusters_by_id[cluster_id].append(face)

    cluster_records = [
        _build_cluster_record(cluster_id, members)
        for cluster_id, members in sorted(clusters_by_id.items())
    ]

    noise = int(np.sum(labels == -1))
    logger.info(
        "Clustering produced %d clusters (excluding %d noise faces).",
        len(cluster_records),
        noise,
    )
    return faces, cluster_records


def _assign_cluster_ids(labels: Iterable[int]) -> dict[int, str]:
    """Map raw DBSCAN labels (0..N, with -1 for noise) to ``cluster_XXXX`` ids.

    Ordering is by descending cluster size so larger clusters get lower ids.
    """

    sizes: dict[int, int] = defaultdict(int)
    for raw in labels:
        sizes[int(raw)] += 1

    ordered = sorted(
        (raw for raw in sizes if raw != -1),
        key=lambda raw: (-sizes[raw], raw),
    )
    return {raw: f"cluster_{i + 1:04d}" for i, raw in enumerate(ordered)}


def _build_cluster_record(cluster_id: str, members: list[FaceDetection]) -> Cluster:
    representative = max(members, key=lambda f: f.confidence)
    photo_ids = sorted({m.photo_id for m in members})
    return Cluster(
        cluster_id=cluster_id,
        representative_face_id=representative.face_id,
        photo_ids=photo_ids,
        face_count=len(members),
    )
