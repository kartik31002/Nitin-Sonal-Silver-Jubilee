"""Copy generated assets into the website's ``public/data`` directory."""

from __future__ import annotations

import shutil
from pathlib import Path

from .config import Paths
from .logging_utils import get_logger

logger = get_logger(__name__)


def deploy_to_website(paths: Paths) -> None:
    """Mirror ``output/`` into ``website/public/data/`` so Vite picks it up."""

    public_data = paths.website_public_data_dir
    public_data.mkdir(parents=True, exist_ok=True)

    site_data_file = paths.site_data_dir / "people.json"
    if not site_data_file.exists():
        raise FileNotFoundError(
            f"{site_data_file} not found. Run `photo-finder generate-site` first."
        )

    target_payload = public_data / "people.json"
    shutil.copyfile(site_data_file, target_payload)
    logger.info("Copied %s -> %s", site_data_file, target_payload)

    _mirror_directory(paths.faces_dir, public_data / "faces")
    _mirror_directory(paths.thumbs_dir, public_data / "photo-thumbnails")


def _mirror_directory(source: Path, destination: Path) -> None:
    if not source.exists():
        logger.warning("Source directory missing, skipping: %s", source)
        return
    if destination.exists():
        shutil.rmtree(destination)
    shutil.copytree(source, destination)
    count = sum(1 for _ in destination.glob("*"))
    logger.info("Copied %d files into %s", count, destination)
