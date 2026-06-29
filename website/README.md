# VialPilot Documentation Site

Static documentation for [VialPilot Swarm](https://github.com/SahilRakhaiya05/VialPilot).

## Deploy to Vercel

**Option A — Dashboard**

1. Import `SahilRakhaiya05/VialPilot` on [vercel.com](https://vercel.com)
2. Root `vercel.json` already sets `outputDirectory: website`
3. Deploy — no build step needed

**Option B — CLI**

```bash
npm i -g vercel
cd ..   # repo root
vercel
```

## Pages

| File | Route |
|------|-------|
| `index.html` | `/` |
| `getting-started.html` | `/getting-started` |
| `architecture.html` | `/architecture` |
| `api.html` | `/api` |

## After deploy

Set in the main app `.env`:

```env
DOCS_SITE_URL=https://your-project.vercel.app
```

The VialPilot nav will show a **Docs** link to your live site.