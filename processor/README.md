# Processor

Python pipeline that turns a Google Drive folder into the static assets used by
the Family Function Photo Finder website.

## Setup

```bash
uv sync
```

## Configure

- Edit `config.yaml`.
- Place your Google OAuth client at `credentials.json`
  (Google Cloud -> APIs & Services -> Credentials -> OAuth client ID, *Desktop*).

## Run

```bash
uv run photo-finder process --folder-url "https://drive.google.com/drive/folders/..."
uv run photo-finder review
uv run photo-finder generate-site
uv run photo-finder deploy
```

See the root `README.md` for the end-to-end story.
