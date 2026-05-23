import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import streamlit as st
import folium
from folium.plugins import HeatMap
from streamlit_folium import st_folium

from src.api import loader, pipeline
from src.api.day_night import is_night_now

st.set_page_config(page_title="SafePath", page_icon="🗺️", layout="wide")


@st.cache_resource(show_spinner="Loading SafePath data...")
def startup():
    loader.download_data()
    rg        = loader.load_graph()
    crime_pts = loader.load_crime_points()
    return rg, crime_pts


rg, crime_pts = startup()

# ── Layout ─────────────────────────────────────────────────────────────────────

col_left, col_right = st.columns([1, 3])

# ── Left column — inputs, route cards, turn-by-turn ───────────────────────────

with col_left:
    tod_icon = "🌙" if is_night_now() else "☀️"
    st.title(f"🗺️ SafePath {tod_icon}")
    st.caption("Safe walking routes for San Diego")

    origin      = st.text_input("Start", placeholder="e.g. Petco Park, San Diego")
    destination = st.text_input("Destination", placeholder="e.g. Balboa Park, San Diego")
    find_btn    = st.button("Find Route", type="primary", use_container_width=True)

    if find_btn:
        if not origin or not destination:
            st.error("Please enter both a start and destination.")
        else:
            with st.spinner("Finding routes..."):
                try:
                    st.session_state.result = pipeline.run(origin, destination)
                    st.session_state.error  = None
                except ValueError as e:
                    st.session_state.error  = str(e)
                    st.session_state.result = None
                except Exception as e:
                    st.session_state.error  = f"Something went wrong: {e}"
                    st.session_state.result = None

    if st.session_state.get("error"):
        st.error(st.session_state.error)

    if st.session_state.get("result"):
        data = st.session_state.result

        ROUTE_CFG = {
            "safest":   ("🔵 Safest",   "#0096FF"),
            "fastest":  ("🟢 Fastest",  "#66FF00"),
            "balanced": ("🔴 Balanced", "#FF0000"),
        }
        for mode, (label, color) in ROUTE_CFG.items():
            r = data["routes"][mode]
            st.markdown(
                f"<div style='border-left: 4px solid {color}; padding: 8px 12px; margin-bottom: 8px;'>"
                f"<b>{label}</b><br>{r['distance_mi']:.1f} mi · {r['time_min']} min"
                f"</div>",
                unsafe_allow_html=True
            )

        with st.expander("Turn-by-turn directions (Safest)"):
            for step in data["routes"]["safest"]["steps"]:
                st.markdown(f"{step['icon']} {step['instruction']} — *{step['distance']}*")

# ── Right column — folium map ─────────────────────────────────────────────────

with col_right:
    center = [32.7157, -117.1611]
    zoom   = 13

    if st.session_state.get("result"):
        data   = st.session_state.result
        center = list(data["origin_coords"])
        zoom   = 14

    m = folium.Map(location=center, zoom_start=zoom, tiles="CartoDB dark_matter")

    if st.session_state.get("result"):
        data = st.session_state.result

        ROUTES = {
            "fastest":  {"color": "#66FF00", "weight": 5, "dash_array": None,  "opacity": 0.85},
            "safest":   {"color": "#0096FF", "weight": 5, "dash_array": None,  "opacity": 0.95},
            "balanced": {"color": "#FF0000", "weight": 3, "dash_array": "6 6", "opacity": 1.0},
        }

        all_coords = []
        for mode, cfg in ROUTES.items():
            coords = data["routes"][mode]["coords"]
            all_coords.extend(coords)
            folium.PolyLine(
                locations=coords,
                color=cfg["color"],
                weight=cfg["weight"],
                dash_array=cfg["dash_array"],
                opacity=cfg["opacity"],
                tooltip=mode.capitalize(),
            ).add_to(m)

        folium.CircleMarker(
            location=data["origin_coords"],
            radius=10, color="#fff", weight=2,
            fill=True, fill_color="#66FF00", fill_opacity=1,
            tooltip="Start"
        ).add_to(m)

        folium.CircleMarker(
            location=data["destination_coords"],
            radius=10, color="#fff", weight=2,
            fill=True, fill_color="#FF4444", fill_opacity=1,
            tooltip="Destination"
        ).add_to(m)

        heat_pts = [[lat, lng] for lat, lng in data["crime_pts"]]
        if heat_pts:
            HeatMap(heat_pts, radius=15, blur=10, max_zoom=13).add_to(m)

        if all_coords:
            m.fit_bounds(all_coords)

    st_folium(m, use_container_width=True, height=700)
