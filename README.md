# Family Function Photo Finder

A complete pipeline that turns a Google Drive folder of event photos into a static
website where guests can find every photo they appear in by tapping their face.

- **Processor**: Python pipeline that downloads photos from Google Drive,
  detects faces (InsightFace), clusters them (DBSCAN), generates thumbnails,
  and emits metadata for the website.
- **Website**: React + TypeScript + Vite + TailwindCSS single-page app.
  Loads metadata as static JSON, never touches a backend.
- **Originals stay in Google Drive.** Only thumbnails and metadata are hosted.

```
family-photo-finder/
├── processor/                 # Python processing pipeline (uv)
├── website/                   # React + TS + Vite frontend
├── output/
│   ├── website-data/          # people.json
│   ├── faces/                 # cluster_XXXX.jpg face thumbnails
│   ├── photo-thumbnails/      # thumb_XXXXXX.jpg photo thumbnails
│   └── review/                # static review UI for naming clusters
└── README.md
```

## Quick start

### 1. Install the processor

```bash
cd processor
uv sync
```

### 2. Configure

Edit `processor/config.yaml`:

```yaml
event_title: Gupta Family Wedding
google_drive_folder: "https://drive.google.com/drive/folders/..."
thumbnail_size: 400
face_thumbnail_size: 256
dbscan_eps: 0.45
dbscan_min_samples: 2
```

Drop your Google API OAuth client into `processor/credentials.json`
(see *Google Drive credentials* below).

### 3. Run the full pipeline

```bash
uv run photo-finder process \
  --folder-url "https://drive.google.com/drive/folders/FOLDER_ID"
```

This downloads photos to `processor/cache/`, detects + clusters faces, writes
thumbnails to `../output/`, and removes the cache when finished.

### 4. Name the clusters

```bash
uv run photo-finder review
```

Opens `output/review/index.html`. Type a name under each cluster, save, and
export `labels.json`. Unnamed clusters become `Person 1`, `Person 2`, etc.

### 5. Build the website data

```bash
uv run photo-finder generate-site
```

Writes `output/website-data/people.json`.

### 6. Deploy assets into the website

```bash
uv run photo-finder deploy
```

Copies `faces/`, `photo-thumbnails/`, and `people.json` into
`website/public/data/`.

### 7. Build and ship the website

```bash
cd ../website
npm install
npm run build
```

The contents of `website/dist/` can be uploaded to GitHub Pages,
Cloudflare Pages, Netlify, or any static host.

For GitHub Pages, push the repo and the included
[`.github/workflows/deploy.yml`](./.github/workflows/deploy.yml) handles the
build + publish automatically.
See [`DEPLOYMENT.md`](./DEPLOYMENT.md) for the full walkthrough.

## Google Drive credentials

The processor uses the official Google Drive API.

1. Create a Google Cloud project.
2. Enable the **Google Drive API**.
3. Create an **OAuth client ID** of type *Desktop app*.
4. Download the JSON file and save it as `processor/credentials.json`.
5. On first run the CLI opens a browser for consent and writes
   `processor/token.json` for reuse.

Only **read** scope (`drive.readonly`) is requested.

## Architecture

See [`ARCHITECTURE.md`](./ARCHITECTURE.md) for a deeper walkthrough of the
pipeline, data shapes, and deployment topology.

## CLI reference

| Command                              | Purpose                                       |
| ------------------------------------ | --------------------------------------------- |
| `photo-finder process --folder-url`  | Full ingest + detection + clustering + thumbs |
| `photo-finder review`                | Launch the static cluster-naming UI           |
| `photo-finder generate-site`         | Emit `output/website-data/people.json`        |
| `photo-finder deploy`                | Copy generated assets into `website/public/`  |

## Performance targets

- 5,000 photos
- 200+ people
- <2 second initial load on the website

The website achieves this with code splitting, lazy image loading, `React.memo`,
and a virtualized photo grid.
