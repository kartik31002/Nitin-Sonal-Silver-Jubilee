"""Generates the static cluster review UI under output/review/."""

from __future__ import annotations

import json
import shutil
from pathlib import Path

from .logging_utils import get_logger
from .models import Cluster, FaceDetection

logger = get_logger(__name__)


REVIEW_HTML = """<!doctype html>
<html lang=\"en\">
<head>
  <meta charset=\"utf-8\" />
  <meta name=\"viewport\" content=\"width=device-width,initial-scale=1\" />
  <title>Cluster Review</title>
  <style>
    :root { color-scheme: light dark; }
    * { box-sizing: border-box; }
    body { font-family: -apple-system, BlinkMacSystemFont, \"Segoe UI\", Roboto, sans-serif; margin: 0; background: #0f1115; color: #e7e9ee; }
    header { position: sticky; top: 0; z-index: 10; background: rgba(15,17,21,0.95); backdrop-filter: blur(8px); padding: 16px 24px; border-bottom: 1px solid #222631; display: flex; gap: 12px; align-items: center; flex-wrap: wrap; }
    header h1 { font-size: 18px; margin: 0; flex: 1; }
    header button { background: #6366f1; color: white; border: none; border-radius: 8px; padding: 10px 16px; font-size: 14px; cursor: pointer; font-weight: 500; }
    header button.secondary { background: #2a2f3a; }
    header button:hover { filter: brightness(1.1); }
    header .progress { font-size: 13px; opacity: 0.7; }
    main { padding: 24px; max-width: 920px; margin: 0 auto; }
    .cluster { background: #161922; border: 1px solid #232735; border-radius: 16px; padding: 20px; margin-bottom: 20px; scroll-margin-top: 100px; }
    .cluster.active { border-color: #6366f1; box-shadow: 0 0 0 2px rgba(99,102,241,0.25); }
    .cluster h2 { font-size: 16px; margin: 0 0 12px; opacity: 0.85; }
    .faces { display: flex; gap: 10px; flex-wrap: wrap; margin-bottom: 14px; }
    .faces img { width: 96px; height: 96px; object-fit: cover; border-radius: 12px; border: 1px solid #2a2f3a; background: #1f2330; }
    .faces .more { width: 96px; height: 96px; border-radius: 12px; background: #1f2330; display: flex; align-items: center; justify-content: center; font-size: 13px; opacity: 0.7; }
    input[type=text] { width: 100%; padding: 12px 14px; border-radius: 10px; border: 1px solid #2a2f3a; background: #0f1115; color: #e7e9ee; font-size: 15px; }
    input[type=text]:focus { outline: none; border-color: #6366f1; }
    .hint { font-size: 12px; opacity: 0.55; margin-top: 8px; }
    .saved { color: #34d399; font-size: 12px; margin-left: 8px; }
    .empty { text-align: center; padding: 80px 16px; opacity: 0.6; }
  </style>
</head>
<body>
  <header>
    <h1>Cluster Review</h1>
    <span class=\"progress\" id=\"progress\"></span>
    <button class=\"secondary\" id=\"save-btn\">Save progress</button>
    <button id=\"export-btn\">Export labels.json</button>
  </header>
  <main id=\"app\"></main>
  <script id=\"review-data\" type=\"application/json\">__REVIEW_DATA__</script>
  <script>
    const data = JSON.parse(document.getElementById('review-data').textContent);
    const storageKey = 'family-photo-finder.labels.v1';
    const stored = JSON.parse(localStorage.getItem(storageKey) || '{}');
    const labels = Object.assign({}, data.labels || {}, stored);

    const app = document.getElementById('app');
    const progress = document.getElementById('progress');

    function persist() {
      localStorage.setItem(storageKey, JSON.stringify(labels));
    }

    function updateProgress() {
      const total = data.clusters.length;
      const named = data.clusters.filter(c => (labels[c.id] || '').trim().length > 0).length;
      progress.textContent = `${named} / ${total} named`;
    }

    function focusCluster(index) {
      const inputs = app.querySelectorAll('input[type=text]');
      if (inputs[index]) {
        inputs[index].focus();
        inputs[index].scrollIntoView({ behavior: 'smooth', block: 'center' });
      }
    }

    function render() {
      app.innerHTML = '';
      if (data.clusters.length === 0) {
        const empty = document.createElement('div');
        empty.className = 'empty';
        empty.textContent = 'No clusters yet. Run `photo-finder process` first.';
        app.appendChild(empty);
        updateProgress();
        return;
      }

      data.clusters.forEach((cluster, index) => {
        const wrap = document.createElement('section');
        wrap.className = 'cluster';
        wrap.id = cluster.id;

        const title = document.createElement('h2');
        title.textContent = `${cluster.id} \u2014 ${cluster.faceCount} face${cluster.faceCount === 1 ? '' : 's'} across ${cluster.photoCount} photo${cluster.photoCount === 1 ? '' : 's'}`;
        wrap.appendChild(title);

        const faces = document.createElement('div');
        faces.className = 'faces';
        const samples = cluster.sampleFaces.length > 0 ? cluster.sampleFaces : [cluster.faceThumbnail];
        samples.slice(0, 8).forEach(src => {
          const img = document.createElement('img');
          img.src = src;
          img.loading = 'lazy';
          img.alt = cluster.id;
          faces.appendChild(img);
        });
        if (samples.length > 8) {
          const more = document.createElement('div');
          more.className = 'more';
          more.textContent = `+${samples.length - 8}`;
          faces.appendChild(more);
        }
        wrap.appendChild(faces);

        const input = document.createElement('input');
        input.type = 'text';
        input.placeholder = `Name for ${cluster.id} (blank = \"Person ${index + 1}\")`;
        input.value = labels[cluster.id] || '';
        input.dataset.cluster = cluster.id;
        input.addEventListener('input', () => {
          labels[cluster.id] = input.value;
          persist();
          updateProgress();
        });
        input.addEventListener('keydown', event => {
          if (event.key === 'Enter') {
            event.preventDefault();
            focusCluster(index + 1);
          } else if (event.key === 'ArrowDown' && (event.metaKey || event.ctrlKey)) {
            event.preventDefault();
            focusCluster(index + 1);
          } else if (event.key === 'ArrowUp' && (event.metaKey || event.ctrlKey)) {
            event.preventDefault();
            focusCluster(index - 1);
          }
        });
        wrap.appendChild(input);

        const hint = document.createElement('div');
        hint.className = 'hint';
        hint.textContent = 'Enter to jump to the next cluster. Cmd/Ctrl + Arrow to navigate.';
        wrap.appendChild(hint);

        app.appendChild(wrap);
      });
      updateProgress();
    }

    document.getElementById('save-btn').addEventListener('click', () => {
      persist();
      const note = document.createElement('span');
      note.className = 'saved';
      note.textContent = 'Saved';
      document.querySelector('header').appendChild(note);
      setTimeout(() => note.remove(), 1200);
    });

    document.getElementById('export-btn').addEventListener('click', () => {
      const payload = {};
      data.clusters.forEach((cluster, index) => {
        const value = (labels[cluster.id] || '').trim();
        payload[cluster.id] = value || `Person ${index + 1}`;
      });
      const blob = new Blob([JSON.stringify(payload, null, 2)], { type: 'application/json' });
      const url = URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.download = 'labels.json';
      document.body.appendChild(link);
      link.click();
      link.remove();
      URL.revokeObjectURL(url);
    });

    render();
  </script>
</body>
</html>
"""


class Reviewer:
    """Renders ``output/review/index.html`` and copies face assets next to it."""

    def __init__(self, review_dir: Path, faces_dir: Path) -> None:
        self.review_dir = review_dir
        self.faces_dir = faces_dir

    def write(
        self,
        clusters: list[Cluster],
        faces: list[FaceDetection],
        cluster_samples_dir: Path | None = None,
        existing_labels: dict[str, str] | None = None,
    ) -> Path:
        self.review_dir.mkdir(parents=True, exist_ok=True)

        review_faces_dir = self.review_dir / "faces"
        review_faces_dir.mkdir(parents=True, exist_ok=True)
        if self.faces_dir.exists():
            for src in self.faces_dir.glob("*.jpg"):
                try:
                    shutil.copyfile(src, review_faces_dir / src.name)
                except Exception as exc:  # noqa: BLE001
                    logger.warning("Failed to copy face thumb %s: %s", src, exc)

        review_samples_dir = self.review_dir / "samples"
        if cluster_samples_dir is not None and cluster_samples_dir.exists():
            if review_samples_dir.exists():
                shutil.rmtree(review_samples_dir)
            shutil.copytree(cluster_samples_dir, review_samples_dir)

        faces_by_cluster: dict[str, list[FaceDetection]] = {}
        for face in faces:
            if face.cluster_id is None:
                continue
            faces_by_cluster.setdefault(face.cluster_id, []).append(face)

        cluster_payload = []
        for cluster in clusters:
            sample_files = []
            sample_dir = review_samples_dir / cluster.cluster_id
            if sample_dir.exists():
                sample_files = [
                    f"samples/{cluster.cluster_id}/{p.name}"
                    for p in sorted(sample_dir.glob("*.jpg"))
                ]
            cluster_payload.append(
                {
                    "id": cluster.cluster_id,
                    "faceCount": cluster.face_count,
                    "photoCount": len(cluster.photo_ids),
                    "faceThumbnail": f"faces/{cluster.cluster_id}.jpg",
                    "sampleFaces": sample_files,
                }
            )

        review_payload = {
            "clusters": cluster_payload,
            "labels": existing_labels or {},
        }

        html = REVIEW_HTML.replace(
            "__REVIEW_DATA__", json.dumps(review_payload).replace("</", "<\\/")
        )
        target = self.review_dir / "index.html"
        target.write_text(html, encoding="utf-8")
        logger.info("Wrote review UI to %s", target)
        return target
