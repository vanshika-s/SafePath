"""SafePath Streamlit frontend — calls the FastAPI backend via HTTP.

Set SAFEPATH_BACKEND_URL env var to point at your Render deployment URL.
Defaults to http://localhost:8000 for local development.
"""

import os
import requests
import streamlit as st
import folium
from folium.plugins import HeatMap
from streamlit_folium import st_folium

BACKEND_URL = os.environ.get("SAFEPATH_BACKEND_URL", "http://localhost:8000").rstrip("/")

ROUTE_CFG = {
    "safest":   {"label": "Safest",   "icon": "🛡️", "color": "#0096FF", "weight": 5},
    "balanced": {"label": "Balanced", "icon": "⚖️", "color": "#FF4444", "weight": 3},
    "fastest":  {"label": "Fastest",  "icon": "⚡", "color": "#66FF00", "weight": 5},
}

SD_CENTER = [32.7157, -117.1611]


st.set_page_config(
    page_title="SafePath SD",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Sidebar ────────────────────────────────────────────────────────────────────

with st.sidebar:
    st.markdown("## 🛡️ SafePath")
    st.caption("Safer walking routes in San Diego")
    st.divider()

    origin = st.text_input(
        "From",
        placeholder="e.g. 5th Ave & Market St, San Diego",
        key="origin",
    )
    destination = st.text_input(
        "To",
        placeholder="e.g. Balboa Park, San Diego, CA",
        key="destination",
    )

    st.divider()

    route_mode = st.radio(
        "Route preference",
        list(ROUTE_CFG.keys()),
        format_func=lambda k: f"{ROUTE_CFG[k]['icon']} {ROUTE_CFG[k]['label']}",
        key="route_mode",
    )

    show_heatmap = st.checkbox("Show crime heatmap", value=True, key="show_heatmap")

    find = st.button("Find Route", type="primary", use_container_width=True)

    # ── Trigger route fetch ────────────────────────────────────────────────────
    if find:
        if not origin.strip() or not destination.strip():
            st.error("Enter both origin and destination.")
        else:
            with st.spinner("Finding safe route…"):
                try:
                    resp = requests.post(
                        f"{BACKEND_URL}/route",
                        json={"origin": origin, "destination": destination},
                        timeout=120,
                    )
                    if resp.status_code == 200:
                        st.session_state["result"] = resp.json()
                    else:
                        st.error(resp.json().get("detail", "Route not found."))
                        st.session_state.pop("result", None)
                except requests.exceptions.ConnectionError:
                    st.error(f"Cannot reach backend at {BACKEND_URL}. Is it running?")
                except requests.exceptions.Timeout:
                    st.error("Request timed out — backend may be cold-starting. Try again.")
                except Exception as exc:
                    st.error(f"Unexpected error: {exc}")

    # ── Route summary + directions ─────────────────────────────────────────────
    result = st.session_state.get("result")
    if result:
        active = st.session_state.get("route_mode", "safest")
        mode_data = result["routes"].get(active, {})

        st.divider()
        col_a, col_b = st.columns(2)
        col_a.metric("Distance", f"{mode_data.get('distance_mi', '—')} mi")
        col_b.metric("Walk time", f"{mode_data.get('time_min', '—')} min")

        is_night = result.get("is_night", False)
        st.caption("🌙 Night mode — using night safety weights" if is_night
                   else "☀️ Day mode — using day safety weights")

        steps = mode_data.get("steps", [])
        if steps:
            st.divider()
            st.markdown("**Step-by-step directions**")
            for step in steps:
                icon = step.get("icon", "•")
                instr = step.get("instruction", "")
                dist = step.get("distance", "")
                suffix = f"  *{dist}*" if dist else ""
                st.markdown(f"{icon} {instr}{suffix}")


# ── Map (main area) ────────────────────────────────────────────────────────────

result = st.session_state.get("result")
active_mode = st.session_state.get("route_mode", "safest")

center = SD_CENTER
zoom = 13

if result:
    oc = result["origin_coords"]
    dc = result["destination_coords"]
    center = [(oc[0] + dc[0]) / 2, (oc[1] + dc[1]) / 2]

m = folium.Map(
    location=center,
    zoom_start=zoom,
    tiles="https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png",
    attr='&copy; <a href="https://www.openstreetmap.org/copyright">OSM</a> &copy; <a href="https://carto.com/">CARTO</a>',
)

# Crime heatmap
if result and st.session_state.get("show_heatmap", True):
    crime_pts = result.get("crime_pts", [])
    if crime_pts:
        HeatMap(
            [[p[0], p[1]] for p in crime_pts],
            radius=10,
            blur=15,
            max_zoom=15,
            gradient={"0.4": "blue", "0.65": "lime", "1": "red"},
        ).add_to(m)

# Routes
if result:
    # Draw inactive routes first (lower z-order)
    for mode in [m for m in ROUTE_CFG if m != active_mode]:
        data = result["routes"].get(mode, {})
        coords = data.get("coords", [])
        if not coords:
            continue
        cfg = ROUTE_CFG[mode]
        folium.PolyLine(
            coords,
            color=cfg["color"],
            weight=cfg["weight"],
            opacity=0.35,
            tooltip=f"{cfg['icon']} {cfg['label']}",
        ).add_to(m)

    # Draw active route on top
    active_data = result["routes"].get(active_mode, {})
    active_coords = active_data.get("coords", [])
    if active_coords:
        cfg = ROUTE_CFG[active_mode]
        folium.PolyLine(
            active_coords,
            color=cfg["color"],
            weight=cfg["weight"] + 2,
            opacity=1.0,
            tooltip=f"{cfg['icon']} {cfg['label']} (selected)",
        ).add_to(m)

    # Origin / destination markers
    oc = result["origin_coords"]
    dc = result["destination_coords"]
    folium.Marker(
        [oc[0], oc[1]],
        tooltip="Start",
        icon=folium.Icon(color="green", icon="circle", prefix="fa"),
    ).add_to(m)
    folium.Marker(
        [dc[0], dc[1]],
        tooltip="Destination",
        icon=folium.Icon(color="red", icon="flag", prefix="fa"),
    ).add_to(m)

st_folium(m, use_container_width=True, height=720, returned_objects=[])
