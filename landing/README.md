# SafePath — Web Frontend & API

This folder is the custom web frontend for SafePath. It is **separate from the Streamlit app** (`app/app.py`) and is served by a small FastAPI backend (`app/api_server.py`) that wraps the exact same routing engine (`src/api/pipeline.py`).

```
landing/
├── index.html   ← marketing landing page (static)
├── app.html     ← interactive routing app  (static, calls /api/route)
├── routes.js    ← precomputed demo route for the landing page
└── README.md    ← you are here
```

## What serves what

| URL | Serves | Needs Python? |
|-----|--------|---------------|
| `/`            | `index.html` (landing) | no (static) |
| `/app`         | `app.html` (the app)   | no for the page, **yes** for routing |
| `/routes.js`   | demo data              | no |
| `/api/route?origin=…&destination=…` | live routes as JSON | **yes** — runs the engine |

The landing page is fully static. The **app** needs the API to compute real routes, and the API needs Python (loads the graph + crime data and runs Dijkstra).

---

## Run locally

```bash
pip install -r requirements.txt
uvicorn app.api_server:app --port 8000
```

Then open:
- http://localhost:8000  → landing page
- http://localhost:8000/app → the routing app

On first run it downloads `fast_graph.zip` + `crime_final_gdf.gpkg` from Google Cloud Storage (~30s), then it's fast.

---

## Deploy

There are two independent things you can deploy. Pick based on what you need.

### Option A — Streamlit Cloud (the Streamlit app only)
This deploys `app/app.py`, **not** this web frontend.
1. Push to GitHub.
2. On [share.streamlit.io](https://share.streamlit.io): New app → repo → branch `main` → main file `app/app.py`.
3. Done. (No web server config needed; Streamlit handles it.)

> Streamlit Cloud **cannot** serve `index.html` / `app.html` / the FastAPI API. Use Option B for the custom frontend.

### Option B — FastAPI app (landing + app + API) on a Python host
Streamlit Cloud only runs Streamlit, so the FastAPI version goes on a host that runs arbitrary Python web servers — **Render**, **Railway**, or **Fly.io** (all have free tiers).

**Start command (all hosts):**
```bash
uvicorn app.api_server:app --host 0.0.0.0 --port $PORT
```

#### Render (easiest)
1. Push to GitHub.
2. [render.com](https://render.com) → New → **Web Service** → connect the repo.
3. Settings:
   - **Environment:** Python 3
   - **Build command:** `pip install -r requirements.txt`
   - **Start command:** `uvicorn app.api_server:app --host 0.0.0.0 --port $PORT`
4. Create. First boot downloads the data from GCS (~30s), then it serves `/`, `/app`, and `/api/route`.

#### Railway
1. [railway.app](https://railway.app) → New Project → Deploy from GitHub repo.
2. It auto-detects Python. Set the start command (Settings → Deploy):
   `uvicorn app.api_server:app --host 0.0.0.0 --port $PORT`
3. Deploy.

#### Fly.io
1. `fly launch` (creates a `fly.toml`; choose no DB).
2. Set the internal port to match `$PORT`, or hardcode `--port 8080` and set `internal_port = 8080` in `fly.toml`.
3. `fly deploy`.

### Notes for any Python host
- `requirements.txt` already includes `fastapi` and `uvicorn`.
- The data files are **not** in git — they download from public GCS on first boot, so no upload step is needed. Containers that reset will re-download on next cold start (fine for a demo).
- Free tiers may sleep when idle; the first request after sleeping will be slow (cold start + data download).

---

## Why two frontends?
- **Streamlit app** (`app/app.py`): fastest to deploy, good for the team/grading via Streamlit Cloud.
- **Web frontend** (`landing/`): the polished, animated, Google-Maps-style experience — landing page + app — for a public showcase. Same engine underneath, so routes and scores are identical.
</content>
