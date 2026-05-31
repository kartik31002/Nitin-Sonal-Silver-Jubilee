# Architecture

```text
┌──────────────┐    ┌──────────────────────────────────────────────────────┐    ┌──────────────┐
│ Google Drive │ ──>│                      Processor                       │ ──>│   Website    │
│   folder     │    │  download -> detect -> cluster -> thumbnail -> emit  │    │ (static SPA) │
└──────────────┘    └──────────────────────────────────────────────────────┘    └──────────────┘
                                       │
                                       ▼
                         output/{faces, photo-thumbnails,
                         review, website-data}
```

## Processor pipeline

```
┌─────────────────────┐
│  drive.DriveClient  │  authenticate + list + stream-download
└──────────┬──────────┘
           ▼
┌─────────────────────┐
│   cache.ImageCache  │  temp originals in processor/cache/
└──────────┬──────────┘
           ▼
┌─────────────────────┐
│  detect.FaceDetector│  InsightFace buffalo_l -> bbox, conf, 512-d embedding
└──────────┬──────────┘
           ▼
┌─────────────────────┐
│ cluster.FaceCluster │  DBSCAN(cosine, eps, min_samples) -> cluster_XXXX
└──────────┬──────────┘
           ▼
┌─────────────────────┐
│ thumbs.Thumbnailer  │  face thumbnails 256x256, photo thumbnails 400w
└──────────┬──────────┘
           ▼
┌─────────────────────┐
│   review.Reviewer   │  static HTML for naming clusters
└──────────┬──────────┘
           ▼
┌─────────────────────┐
│   site.SiteBuilder  │  emits website-data/people.json
└─────────────────────┘
```

## State files

| File                                  | Purpose                                                       |
| ------------------------------------- | ------------------------------------------------------------- |
| `processor/state/photos.json`         | photo records: id, drive id, dimensions, thumb name           |
| `processor/state/faces.json`          | every detected face with bbox, confidence, embedding, cluster |
| `processor/state/clusters.json`       | cluster id -> representative face + photo count               |
| `processor/state/labels.json`         | cluster id -> human name (produced by review UI)              |
| `output/website-data/people.json`     | final SPA payload                                             |

Embeddings are stored as float32 arrays in `faces.json` (compact JSON list).
Large datasets could move to numpy `.npy` later without changing the contract.

## Data contract for the website

```jsonc
{
  "eventTitle": "Gupta Family Wedding",
  "generatedAt": "2026-05-31T12:00:00Z",
  "people": [
    {
      "id": "cluster_0001",
      "name": "Raj",
      "faceThumbnail": "data/faces/cluster_0001.jpg",
      "photoCount": 127,
      "photos": [
        {
          "thumbnail": "data/photo-thumbnails/thumb_000001.jpg",
          "driveUrl": "https://drive.google.com/file/d/FILE_ID/view"
        }
      ]
    }
  ]
}
```

## Frontend architecture

```
src/
├── main.tsx              # entry, router, suspense
├── App.tsx               # layout + routes
├── pages/
│   ├── HomePage.tsx      # face grid, search, "Find Me" primary CTA
│   └── PersonPage.tsx    # virtualized photo grid, lazy thumbnails
├── components/
│   ├── FaceCard.tsx      # memoized face card
│   ├── PhotoTile.tsx     # memoized photo tile with native lazy loading
│   ├── VirtualGrid.tsx   # windowed grid for thousands of photos
│   └── SearchBar.tsx
├── data/
│   └── loader.ts         # fetch + cache people.json
└── types.ts              # mirrors people.json shape
```

The home page is the `/` route. Person pages are `/p/:id`. The router uses
`React.lazy` to code-split `PersonPage`, so the initial bundle only carries the
home shell.

## Deployment

The processor is run **once per event** on a developer machine. The website is
a fully static bundle that can be hosted anywhere:

- **GitHub Pages** -> push `website/dist/` to a `gh-pages` branch.
- **Cloudflare Pages** -> point at `website/` with build cmd `npm run build`
  and output dir `dist`.
- **Netlify** -> drag `website/dist/` into the dashboard.

Because guest browsers fetch thumbnails directly from the static host and
original images directly from Google Drive, there is no server, no database,
and no per-request cost beyond static hosting.
