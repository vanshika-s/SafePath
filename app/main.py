# Run with: uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import requests as _requests
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from src.api import loader, pipeline
from src.api.day_night import is_night_now


# ── Startup ───────────────────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    yield


app = FastAPI(title="SafePath", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/static", StaticFiles(directory="app/static"), name="static")


# ── Models ────────────────────────────────────────────────────────────────────

class RouteRequest(BaseModel):
    origin: str
    destination: str


# ── Routes ────────────────────────────────────────────────────────────────────

@app.get("/")
async def index():
    return FileResponse("app/static/index.html")


@app.post("/route")
async def get_route(body: RouteRequest):
    """Geocode both addresses, run Dijkstra × 3, return full route data as JSON."""
    try:
        result = pipeline.run(body.origin, body.destination)
        return result
    except ValueError as e:
        msg = str(e)
        if "geocode" in msg.lower():
            detail = "Could not geocode one or both addresses. Try adding ', San Diego, CA' to your input."
        else:
            detail = msg
        return JSONResponse(status_code=422, content={"detail": detail})
    except Exception as e:
        return JSONResponse(status_code=500, content={"detail": str(e)})


@app.get("/suggest")
async def suggest(q: str):
    """Proxy Nominatim autocomplete, bounded to San Diego."""
    try:
        res = _requests.get(
            "https://nominatim.openstreetmap.org/search",
            params={
                "q": q, "format": "json", "limit": 6,
                "bounded": 1, "viewbox": "-117.65,32.5,-116.9,33.15",
                "countrycodes": "us", "addressdetails": 1,
            },
            headers={"User-Agent": "safepath-sd/1.0"},
            timeout=2,
        )
        return res.json()
    except Exception:
        return []


@app.get("/crime-heatmap")
async def crime_heatmap():
    """Return crime points for the current time-of-day split."""
    crime_pts = loader.load_crime_points()
    tod = "night" if is_night_now() else "day"
    pts = crime_pts[tod]
    return {
        "points":   [{"lat": la, "lng": lo} for la, lo in pts],
        "is_night": tod == "night",
    }
