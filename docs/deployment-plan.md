# Deployment Plan: Mutual Fund FAQ Assistant

> **Backend:** Railway (FastAPI + ChromaDB)  
> **Frontend:** Vercel (Vite + React)  
> **Repository:** [ShaguftaMethwani/chatbot-test](https://github.com/ShaguftaMethwani/chatbot-test)

---

## Table of Contents

1. [Architecture Overview](#1-architecture-overview)
2. [Critical Deployment Considerations](#2-critical-deployment-considerations)
3. [Backend — Railway](#3-backend--railway)
4. [Frontend — Vercel](#4-frontend--vercel)
5. [Post-Deployment Wiring](#5-post-deployment-wiring)
6. [Environment Variables Reference](#6-environment-variables-reference)
7. [GitHub Actions Update](#7-github-actions-update)
8. [Deployment Checklist](#8-deployment-checklist)

---

## 1. Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│  GitHub (ShaguftaMethwani/chatbot-test)                         │
│                                                                  │
│  ├── stitch_hdfc_mutual_fund_assistant/   ──────────▶  Vercel   │
│  │   (Vite + React frontend)               (static CDN)         │
│  │                                                               │
│  └── backend/                             ──────────▶  Railway  │
│      (FastAPI + ChromaDB)                  (container)          │
└─────────────────────────────────────────────────────────────────┘
        │                                         │
        │         HTTPS POST /api/chat            │
        └──────────────────────────────────────── ┘
              Vercel calls Railway on every query
```

---

## 2. Critical Deployment Considerations

> [!CAUTION]
> **ChromaDB is file-based and Railway's filesystem is ephemeral.** Every redeploy wipes `/data/chroma_db/`. The vector store must be rebuilt on every container start using `scripts/ingest.py`. The startup command is configured to do this automatically (see §3.3).

> [!IMPORTANT]
> **The frontend hardcodes `http://localhost:8000`** in `App.jsx` line 33. This must be replaced with an environment variable (`VITE_API_URL`) before deploying to Vercel, otherwise the frontend will try to call your laptop instead of Railway.

> [!IMPORTANT]
> **CORS must include the Vercel production URL.** The backend's `CORS_ORIGINS` env var must list the exact Vercel URL or the browser will block all cross-origin requests.

> [!NOTE]
> **`data/chroma_db/` and `data/raw/` are in `.gitignore`** and won't exist in the Railway container on startup. The startup command handles this by running the ingest pipeline before the server starts.

---

## 3. Backend — Railway

### 3.1 Required Files to Create

#### `backend/start.sh` (Railway startup script)

Create this file at `backend/start.sh`:

```bash
#!/bin/bash
set -e

echo "=== Step 1: Run ingestion pipeline ==="
python scripts/ingest.py

echo "=== Step 2: Start FastAPI server ==="
uvicorn backend.api.main:app --host 0.0.0.0 --port ${PORT:-8000}
```

This runs the full scrape → chunk → embed → store pipeline before the server starts,
ensuring ChromaDB is populated even after a fresh deploy.

#### `railway.toml` (at project root)

```toml
[build]
builder = "NIXPACKS"

[deploy]
startCommand = "bash backend/start.sh"
restartPolicyType = "ON_FAILURE"
restartPolicyMaxRetries = 3

[environments.production.deploy]
healthcheckPath = "/api/health"
healthcheckTimeout = 300
```

#### `Procfile` (fallback, at project root)

```
web: bash backend/start.sh
```

### 3.2 Railway Project Setup (Step-by-Step)

1. Go to [railway.app](https://railway.app) → **New Project** → **Deploy from GitHub repo**
2. Select `ShaguftaMethwani/chatbot-test`
3. Railway auto-detects Python. Leave **Root Directory** as `/` (monorepo root)
4. Go to **Settings → Deploy** and set **Start Command** to:
   ```
   bash backend/start.sh
   ```
5. Add all environment variables (see §3.3)
6. Click **Deploy**

> [!NOTE]
> Railway's free plan has a **sleep-on-idle** policy. The first request after inactivity restarts the container and re-runs the ingest pipeline (~2 min). Consider the Hobby plan ($5/mo) to keep the container always-on and avoid cold starts.

### 3.3 Railway Environment Variables

Set these in **Railway → Your Service → Variables**:

| Variable | Value | Notes |
|---|---|---|
| `GROQ_API_KEY` | `gsk_...` | Your Groq API key — the only real secret |
| `GROQ_MODEL` | `llama-3.3-70b-versatile` | |
| `EMBEDDING_MODEL` | `all-MiniLM-L6-v2` | |
| `CHROMA_PERSIST_DIR` | `backend/data/chroma_db` | Relative to project root |
| `CHROMA_COLLECTION` | `mf_facts` | |
| `TOP_K` | `3` | |
| `SIMILARITY_THRESHOLD` | `0.35` | |
| `CORS_ORIGINS` | `["https://your-app.vercel.app"]` | **Set after Vercel deploys** |

> [!WARNING]
> Do **not** set `PORT` manually — Railway injects it automatically. Setting it yourself can cause the health check to fail.

> [!WARNING]
> Set `CORS_ORIGINS` to your Vercel production URL **after** Vercel is deployed. Until then you can use `["*"]` to unblock testing, but update it before going live.

### 3.4 Estimated First Deploy Time

| Step | Duration |
|---|---|
| Build (install ~700MB deps: torch, sentence-transformers, chromadb) | ~4–6 min |
| Ingest pipeline (scrape 5 Groww pages + embed + store) | ~1–2 min |
| Server start | ~10 sec |
| **Total first cold start** | **~6–8 min** |

Subsequent deploys are faster as Railway caches the pip layer.

---

## 4. Frontend — Vercel

### 4.1 Required Code Change — Fix Hardcoded API URL

**This is mandatory before deploying.**

In [App.jsx line 33](file:///Users/shaguftagurmukhdas/Downloads/chatbot/stitch_hdfc_mutual_fund_assistant/src/App.jsx#L33), change:

```diff
-      const response = await fetch('http://localhost:8000/api/chat', {
+      const response = await fetch(`${import.meta.env.VITE_API_URL}/api/chat`, {
```

Then create `stitch_hdfc_mutual_fund_assistant/.env.local` (for local dev — gitignored by Vite automatically):

```env
VITE_API_URL=http://localhost:8000
```

### 4.2 Vercel Project Setup (Step-by-Step)

1. Go to [vercel.com](https://vercel.com) → **Add New Project** → **Import Git Repository**
2. Select `ShaguftaMethwani/chatbot-test`
3. Configure:

| Setting | Value |
|---|---|
| **Framework Preset** | Vite |
| **Root Directory** | `stitch_hdfc_mutual_fund_assistant` |
| **Build Command** | `npm run build` (auto-detected) |
| **Output Directory** | `dist` (auto-detected) |
| **Install Command** | `npm install` (auto-detected) |

4. Add Environment Variable:

| Variable | Value | Environment |
|---|---|---|
| `VITE_API_URL` | `https://your-railway-app.up.railway.app` | Production, Preview |

> [!IMPORTANT]
> In Vite, only variables prefixed with `VITE_` are exposed to the browser bundle. Never put API keys or secrets in `VITE_*` variables.

5. Click **Deploy**. Build takes ~30–60 seconds.

### 4.3 Vercel Auto-Deploy

Vercel automatically redeploys the frontend on every push to `main`. No additional CI configuration needed for the frontend.

---

## 5. Post-Deployment Wiring

After both services are live, you must connect them:

### Step 1 — Update CORS on Railway

Once you have the Vercel URL (e.g. `https://chatbot-test.vercel.app`), update `CORS_ORIGINS` in Railway:

```
["https://chatbot-test.vercel.app"]
```

Railway auto-redeploys when you save a variable change.

### Step 2 — Update `VITE_API_URL` on Vercel

Once you have the Railway URL (e.g. `https://chatbot-test-production.up.railway.app`), update `VITE_API_URL` in Vercel → Settings → Environment Variables. Trigger a redeploy from the Vercel dashboard.

### Step 3 — Smoke Tests

Run these manually after both are connected:

| Test | URL | Expected |
|---|---|---|
| Health check | `GET https://xxx.up.railway.app/api/health` | `{"status":"healthy","vector_store_count":65}` |
| UI loads | Vercel URL | Chat UI with welcome screen and 3 example questions |
| Factual query | Send "What is the expense ratio of HDFC Mid Cap?" | Answer with source badge and date |
| Advisory refusal | Send "Should I invest in HDFC Mid Cap?" | Refusal with AMFI link |
| PII refusal | Send "My PAN is ABCDE1234F" | PII refusal message |
| CORS check | Browser devtools → Network tab | No CORS errors on `/api/chat` calls |

---

## 6. Environment Variables Reference

### Backend (Railway)

| Variable | Required | Default | Description |
|---|---|---|---|
| `GROQ_API_KEY` | ✅ Yes | — | Groq API key for LLaMA 3.3 70B |
| `GROQ_MODEL` | No | `llama-3.3-70b-versatile` | Groq model name |
| `EMBEDDING_MODEL` | No | `all-MiniLM-L6-v2` | Sentence-transformers model |
| `CHROMA_PERSIST_DIR` | No | `data/chroma_db` | Path for ChromaDB files |
| `CHROMA_COLLECTION` | No | `mf_facts` | ChromaDB collection name |
| `TOP_K` | No | `3` | Number of retrieval results |
| `SIMILARITY_THRESHOLD` | No | `0.35` | Min cosine similarity cutoff |
| `CORS_ORIGINS` | ✅ Yes | localhost only | JSON array of allowed origins |
| `PORT` | Auto | — | Injected by Railway — do not set |

### Frontend (Vercel)

| Variable | Required | Description |
|---|---|---|
| `VITE_API_URL` | ✅ Yes | Full URL of Railway backend, no trailing slash |

---

## 7. GitHub Actions Update

The daily ingestion workflow commits `backend/data/raw/*.json` back to the repo. These committed files serve as **fallback data** — if Groww's API is unreachable when Railway restarts, the scraper can use them instead of failing.

### 7.1 Update `.gitignore`

Remove `data/raw/` from `.gitignore` so the committed JSON files reach Railway:

```diff
-# --- Raw Scraped Data ---
-data/raw/
+# --- Raw Scraped Data (kept in repo as Railway cold-start fallback) ---
+# data/raw/ intentionally tracked
```

### 7.2 Add Fallback Logic to `scraper.py`

If the Groww API fails during Railway startup, fall back to the last committed JSON:

```python
# In scrape_all_schemes(), after the `if raw is None: continue` block, add:
if raw is None:
    fallback_path = out_path / f"{search_id}.json"
    if fallback_path.exists():
        import json
        with open(fallback_path, encoding="utf-8") as f:
            normalized = json.load(f)
        logger.warning("Groww API unavailable — using cached data for %s", search_id)
        results.append(normalized)
    else:
        logger.warning("Skipping %s — no fallback data available", search_id)
    continue
```

### 7.3 Add `RAILWAY_TOKEN` Secret to GitHub

To optionally trigger a Railway redeploy after the daily ingest (so Railway picks up fresh data):

1. Get your Railway API token from **Railway → Account → Tokens**
2. Add it as `RAILWAY_TOKEN` in **GitHub → Settings → Secrets and variables → Actions**
3. Add a step to `.github/workflows/daily_ingest.yml`:

```yaml
      - name: Trigger Railway redeploy
        if: success()
        run: |
          curl -X POST \
            -H "Authorization: Bearer ${{ secrets.RAILWAY_TOKEN }}" \
            -H "Content-Type: application/json" \
            -d '{"serviceId":"${{ secrets.RAILWAY_SERVICE_ID }}"}' \
            https://backboard.railway.app/graphql/v2
```

> [!NOTE]
> The Railway redeploy step is optional. Without it, Railway will still serve fresh data on its next natural restart or when you manually redeploy. The daily GitHub Actions job already commits the latest `data/raw/*.json` to the repo.

---

## 8. Deployment Checklist

### Pre-Deployment — Code Changes

- [ ] Fix hardcoded URL in [App.jsx L33](file:///Users/shaguftagurmukhdas/Downloads/chatbot/stitch_hdfc_mutual_fund_assistant/src/App.jsx#L33) → `import.meta.env.VITE_API_URL`
- [ ] Create `stitch_hdfc_mutual_fund_assistant/.env.local` with `VITE_API_URL=http://localhost:8000`
- [ ] Create `backend/start.sh` with ingest + uvicorn start commands
- [ ] Create `railway.toml` at project root
- [ ] Create `Procfile` at project root (fallback)
- [ ] Update `.gitignore` to un-ignore `backend/data/raw/*.json`
- [ ] Add fallback-to-cached-JSON logic in `scraper.py`
- [ ] Commit and push all changes to `main`

### Railway Deployment

- [ ] Create Railway project from `ShaguftaMethwani/chatbot-test`
- [ ] Set Start Command to `bash backend/start.sh`
- [ ] Set `GROQ_API_KEY` and all other env vars
- [ ] Set `CORS_ORIGINS` temporarily to `["*"]` until Vercel URL is known
- [ ] Wait for first deploy — confirm ingest pipeline logs show success
- [ ] Hit `GET /api/health` — confirm `vector_store_count > 0`
- [ ] Copy Railway public URL

### Vercel Deployment

- [ ] Create Vercel project from `ShaguftaMethwani/chatbot-test`
- [ ] Set Root Directory to `stitch_hdfc_mutual_fund_assistant`
- [ ] Set `VITE_API_URL` to Railway URL
- [ ] Deploy — verify build succeeds in ~30–60 sec
- [ ] Copy Vercel production URL

### Post-Deployment Wiring

- [ ] Update `CORS_ORIGINS` on Railway to exact Vercel URL (remove `["*"]`)
- [ ] Confirm Railway auto-redeployed after CORS change
- [ ] Run all 6 smoke tests from §5 Step 3
- [ ] Add `GROQ_API_KEY` as GitHub Actions secret for daily ingest CI
- [ ] Verify GitHub Actions daily ingest workflow completes successfully
