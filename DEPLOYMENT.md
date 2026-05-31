# Deploying to GitHub Pages

Two paths are wired up:

- **Recommended**: GitHub Actions auto-builds and publishes on every push.
- **One-shot manual**: run `npm run deploy` from `website/`.

Both produce the same output. The site is already configured for project-site
URLs (`base: "./"` + `HashRouter`), so no extra config or `404.html` SPA shim
is needed.

## Prerequisites

1. Run the processor end-to-end:
   ```bash
   cd processor
   uv run photo-finder process --folder-url "..."
   uv run photo-finder review            # name your clusters, export labels.json
   uv run photo-finder import-labels ~/Downloads/labels.json
   uv run photo-finder generate-site
   uv run photo-finder deploy            # copies assets into website/public/data/
   ```
   After this, `website/public/data/` contains `people.json`, `faces/`, and
   `photo-thumbnails/`. **These must be committed** so GitHub Pages can serve them.

2. Make sure `website/public/data/` is **not** in any `.gitignore`. It isn't,
   by default — only `node_modules/`, `dist/`, `*.tsbuildinfo` are ignored.

## Option A: GitHub Actions (recommended)

A workflow is already at [`.github/workflows/deploy.yml`](./.github/workflows/deploy.yml).
It triggers on every push to `main` that touches `website/**`, builds the site,
and publishes via the modern Pages API.

### One-time setup

1. **Create a GitHub repo** and push this directory as the repo root:
   ```bash
   cd family-photo-finder
   git init -b main
   git add .
   git commit -m "Initial commit"
   git remote add origin git@github.com:<USER>/<REPO>.git
   git push -u origin main
   ```

2. **Enable Pages with Actions as the source**:
   `https://github.com/<USER>/<REPO>/settings/pages`
   -> *Build and deployment* -> **Source: GitHub Actions**.

3. Watch the first build at
   `https://github.com/<USER>/<REPO>/actions`. When it goes green, the live URL
   appears on the *Deployments* page and on the repo home page:
   `https://<USER>.github.io/<REPO>/`.

### Re-deploying

Just push to `main`. To rebuild without code changes, hit *Run workflow* in the
Actions tab.

## Option B: Manual `gh-pages` push

If you don't want CI at all, deploy from your machine:

```bash
cd website
npm install        # first time only
npm run deploy
```

This builds the site and force-pushes `dist/` to a `gh-pages` branch.

Then in repo settings:
`https://github.com/<USER>/<REPO>/settings/pages`
-> **Source: Deploy from a branch** -> Branch: `gh-pages`, folder: `/ (root)`.

The `deploy` script is defined in `website/package.json` and uses the
[`gh-pages`](https://www.npmjs.com/package/gh-pages) npm package.

## Pushing only the website (alternative repo layout)

If you'd rather keep the processor private and only publish the site, you can
push just the `website/` directory:

```bash
cd website
git init -b main
git add .
git commit -m "Initial site"
git remote add origin git@github.com:<USER>/<REPO>.git
git push -u origin main
```

Then move the workflow file: `.github/workflows/deploy.yml` should live at the
website's repo root, and you can simplify it by removing the
`defaults.run.working-directory: website` lines (everything is already at the
root). The `paths:` filter under `on.push` can also be dropped.

## URL shapes you'll get

- **Project site** (most common): `https://<USER>.github.io/<REPO>/`
- **User/org site**: `https://<USER>.github.io/` (only if the repo is named
  `<USER>.github.io`)
- **Custom domain**: add a `CNAME` file inside `website/public/` containing
  your domain (`photos.example.com`), commit, and configure DNS as per the
  [GitHub Pages docs](https://docs.github.com/en/pages/configuring-a-custom-domain-for-your-github-pages-site).

## Size budgets

GitHub Pages limits:

| Limit                | Value                       |
| -------------------- | --------------------------- |
| Per file             | 100 MB                      |
| Per repo (soft)      | 1 GB                        |
| Bandwidth (soft)     | 100 GB / month              |
| Builds (soft)        | 10 / hour                   |

Photo thumbnails at 400 px wide / quality 82 land around 30–80 KB each, so
even 5,000 photos sit comfortably below the repo cap. Face thumbnails
(256x256) are ~10–20 KB. If your event ever pushes past ~800 MB of thumbnails,
move the assets to Cloudflare R2 / S3 / Backblaze B2 and point the website
at the bucket URL via a small build-time substitution.

## Troubleshooting

- **Assets 404 after deploy**: confirm `vite.config.ts` still has `base: "./"`
  (relative). Absolute paths break project-site subpath deploys.
- **Routing 404s**: we use `HashRouter`, so deep-linking lives in the URL
  fragment (`#/p/cluster_0001`). No `404.html` workaround required.
- **`people.json` 404**: did you run `uv run photo-finder deploy` *before*
  committing? The processor copies generated data into `website/public/data/`.
- **Pages says "GitHub Pages disabled"**: settings -> Pages -> Source must be
  set to "GitHub Actions".

## Privacy note

Thumbnails (faces + photos) are hosted publicly on GitHub Pages. Original
full-resolution photos remain in Google Drive — the website only links out
to them. If a guest opens the Drive link and the photo isn't shared with
them, Drive enforces its own permissions.
