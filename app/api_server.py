"""
SafePath API + static server.

Wraps the same `pipeline.run()` the Streamlit app uses behind a tiny HTTP API,
and serves the custom front-end in `landing/`.

Run locally:
    uvicorn app.api_server:app --reload --port 8000
Then open http://localhost:8000  (landing page) and http://localhost:8000/app
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from src.api import loader, pipeline

_ROOT    = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_LANDING = os.path.join(_ROOT, "landing")

app = FastAPI(title="SafePath API")


@app.on_event("startup")
def _warm() -> None:
    # Download (first run) + load graph and crime data into memory once.
    loader.download_data()
    loader.load_graph()
    loader.load_crime_points()


def _trim_crime(crime_pts: list, routes: dict, buffer: float = 0.01, cap: int = 1500) -> list:
    """Keep only crime points within a small box around the routes (keeps payload light)."""
    lats, lngs = [], []
    for r in routes.values():
        for la, lo in r["coords"]:
            lats.append(la); lngs.append(lo)
    if not lats:
        return []
    la_min, la_max = min(lats) - buffer, max(lats) + buffer
    lo_min, lo_max = min(lngs) - buffer, max(lngs) + buffer
    near = [
        [round(la, 5), round(lo, 5)]
        for la, lo in crime_pts
        if la_min <= la <= la_max and lo_min <= lo <= lo_max
    ]
    if len(near) > cap:
        step = len(near) // cap
        near = near[::step]
    return near


@app.get("/api/route")
def api_route(
    origin: str = Query(..., min_length=2),
    destination: str = Query(..., min_length=2),
):
    try:
        result = pipeline.run(origin, destination)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Routing failed: {e}")

    routes_out = {}
    for mode, r in result["routes"].items():
        sc           = r["edge_scores"]
        total_cost   = sum(e["safety_cost"] for e in sc)
        total_length = sum(e["length_m"]    for e in sc) or 1
        # Length-weighted scores — matches the Streamlit formula:
        # cost = length × (1 + 4 × (1 − score))  →  score = 1 − (cost − length) / (4 × length)
        safety = round(1 - (total_cost - total_length) / (4 * total_length), 3)
        routes_out[mode] = {
            "coords":       [[round(la, 5), round(lo, 5)] for la, lo in r["coords"]],
            "steps":        r["steps"],
            "distance_mi":  r["distance_mi"],
            "time_min":     r["time_min"],
            "safety":       safety,
            "crime_safety": round(sum(e["crime_score"]   * e["length_m"] for e in sc) / total_length, 3),
            "infra":        round(sum(e["infrastructure"] * e["length_m"] for e in sc) / total_length, 3),
            "walk":         round(sum(e["walk_score"]    * e["length_m"] for e in sc) / total_length, 3),
        }

    return JSONResponse({
        "origin":      list(result["origin_coords"]),
        "dest":        list(result["destination_coords"]),
        "is_night":    result["is_night"],
        "routes":      routes_out,
        "crime_pts":   _trim_crime(result["crime_pts"], result["routes"]),
    })


@app.get("/")
def index():
    return FileResponse(os.path.join(_LANDING, "index.html"))


@app.get("/app")
def app_page():
    return FileResponse(os.path.join(_LANDING, "app.html"))


# Serve everything else in landing/ (routes.js, etc.) as static files.
app.mount("/", StaticFiles(directory=_LANDING), name="static")
