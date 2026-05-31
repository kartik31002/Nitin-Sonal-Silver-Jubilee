"""Convenience entry-point so users can run ``python processor/main.py ...``.

The richer Click CLI lives in :mod:`family_photo_finder.cli` and is also
exposed as ``photo-finder`` after ``uv sync``.
"""

from __future__ import annotations

import sys
from pathlib import Path

PROCESSOR_ROOT = Path(__file__).resolve().parent
SRC_PATH = PROCESSOR_ROOT / "src"
if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))

from family_photo_finder.cli import cli  # noqa: E402  (sys.path fix above)


if __name__ == "__main__":
    cli(obj={})
