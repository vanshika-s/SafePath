import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from html import escape
import requests as _requests
import streamlit as st
import folium
from collections import defaultdict
from folium.plugins import HeatMap
from streamlit_folium import st_folium
from streamlit_searchbox import st_searchbox

from datetime import datetime
from astral import LocationInfo
from astral.sun import sun as _astral_sun
from dateutil import tz

from src.api import loader, pipeline
from src.api.day_night import is_night_now

st.set_page_config(page_title="SafePath", page_icon="🛡️", layout="wide")

# ── CSS — dark text on light background ───────────────────────────────────────
st.markdown("""
<style>
/* Route cards */
.rc {
    border: 1.5px solid #d1d5db;
    border-radius: 10px;
    padding: 12px 14px;
    margin-bottom: 4px;
    background: #f9fafb;
}
.rc.active { background: #eff6ff; }
.rc-top {
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin-bottom: 6px;
}
.rc-label {
    display: flex;
    align-items: center;
    gap: 8px;
    font-size: 15px;
    font-weight: 700;
    color: #111827;
}
.rc-dot {
    width: 13px;
    height: 13px;
    border-radius: 50%;
    display: inline-block;
    flex-shrink: 0;
}
.rc-score {
    font-size: 13px;
    background: #e5e7eb;
    padding: 3px 9px;
    border-radius: 8px;
    color: #111827;
    font-weight: 600;
}
.rc-stats { font-size: 14px; color: #111827; }
.rc-val   { color: #111827; font-weight: 600; }

/* Directions */
.dir-step {
    display: flex;
    gap: 12px;
    align-items: flex-start;
    padding: 10px 0;
    border-bottom: 1px solid #d1d5db;
}
.dir-step:last-child { border-bottom: none; }
.dir-icon {
    width: 32px;
    height: 32px;
    background: #e5e7eb;
    border-radius: 50%;
    display: inline-flex;
    align-items: center;
    justify-content: center;
    font-size: 15px;
    flex-shrink: 0;
}
.dir-icon.dest { background: #fee2e2; border: 1px solid #ef4444; }
.dir-body  { flex: 1; min-width: 0; }
.dir-num   { font-size: 12px; color: #374151; font-weight: 700; margin-bottom: 2px; }
.dir-instr { font-size: 15px; color: #111827; line-height: 1.5; font-weight: 600; }
.dir-dist  { font-size: 13px; color: #374151; margin-top: 3px; font-weight: 500; }

/* Section labels */
.sl {
    font-size: 12px;
    font-weight: 700;
    letter-spacing: .08em;
    text-transform: uppercase;
    color: #374151;
    margin: 14px 0 8px 0;
}

/* Brand */
.brand      { display: flex; align-items: center; gap: 10px; margin-bottom: 8px; }
.brand-dot  { width: 12px; height: 12px; border-radius: 50%; background: #2d7a5f; flex-shrink: 0; }
.brand-name { font-size: 22px; font-weight: 800; color: #111827; }

/* Time card */
.time-card-day   { background:#e4edf5; border:1px solid #cdd8e3; border-radius:10px; padding:10px 12px; margin-bottom:12px; }
.time-card-night { background:#dce3f0; border:1px solid #aebdd4; border-radius:10px; padding:10px 12px; margin-bottom:12px; }
.time-main-day   { font-size:15px; font-weight:700; color:#111827; }
.time-main-night { font-size:15px; font-weight:700; color:#111827; }
.time-sub        { font-size:13px; color:#1f2937; margin-top:3px; font-weight:500; }

/* Compare cards */
.cmp-card {
    border-radius: 12px;
    padding: 20px 16px;
    background: #f9fafb;
    text-align: center;
    height: 100%;
}
.cmp-stat-label { color: #111827; font-size: 13px; margin-bottom: 2px; font-weight: 600; }
.cmp-stat-val   { color: #111827; font-size: 24px; font-weight: 700; margin-bottom: 14px; }
.cmp-score-val  { font-size: 24px; font-weight: 700; margin-bottom: 4px; }
.cmp-title      { font-size: 18px; font-weight: 700; color: #111827; margin-bottom: 18px; }

[data-testid="stSidebar"] > div:first-child { padding-top: 1.2rem; }
</style>
""", unsafe_allow_html=True)


# ── Data loading ───────────────────────────────────────────────────────────────
@st.cache_resource(show_spinner="SafePath is loading data for the first time (~30s)…")
def startup():
    loader.download_data()
    loader.load_graph()
    loader.load_crime_points()
    return True

startup()


# ── Autocomplete ───────────────────────────────────────────────────────────────
def suggest_address(query: str) -> list[str]:
    if not query or len(query) < 3:
        return []
    try:
        resp = _requests.get(
            "https://nominatim.openstreetmap.org/search",
            params={
                "q": query, "format": "json", "limit": 6,
                "bounded": 1, "viewbox": "-117.65,32.5,-116.9,33.15",
                "countrycodes": "us", "addressdetails": 1,
            },
            headers={"User-Agent": "safepath-sd/1.0"},
            timeout=2,
        )
        return [r["display_name"] for r in resp.json()]
    except Exception:
        return []


# ── Constants ──────────────────────────────────────────────────────────────────
ROUTE_CFG = {
    "safest":   {"label": "Safest",   "icon": "🛡️", "color": "#0096FF", "weight": 5, "dash": None},
    "fastest":  {"label": "Fastest",  "icon": "⚡",  "color": "#22c55e", "weight": 5, "dash": None},
    "balanced": {"label": "Balanced", "icon": "⚖️",  "color": "#f97316", "weight": 3, "dash": "6 6"},
}

# ── Session defaults ───────────────────────────────────────────────────────────
if "active_mode"      not in st.session_state: st.session_state.active_mode      = "safest"
if "result"           not in st.session_state: st.session_state.result           = None
if "error"            not in st.session_state: st.session_state.error            = None
if "night_dismissed"  not in st.session_state: st.session_state.night_dismissed  = False


def _step_html(i: int, step: dict) -> str:
    """Build one direction step as a single-line HTML string (no blank lines)."""
    is_dest    = step["icon"] == "📍"
    icon_cls   = "dir-icon dest" if is_dest else "dir-icon"
    num_part   = f'<div class="dir-num">Step {i + 1}</div>' if not is_dest else ""
    dist_part  = f'<div class="dir-dist">{escape(step["distance"])}</div>' if step.get("distance") else ""
    instr      = escape(step["instruction"])
    return (
        f'<div class="dir-step">'
        f'<div class="{icon_cls}">{step["icon"]}</div>'
        f'<div class="dir-body">{num_part}'
        f'<div class="dir-instr">{instr}</div>{dist_part}</div>'
        f'</div>'
    )


# ── Sidebar ────────────────────────────────────────────────────────────────────
with st.sidebar:
    tod = is_night_now()

    # Time / day-night card (shown first)
    _local_tz  = tz.tzlocal()
    _now       = datetime.now(_local_tz)
    _loc       = LocationInfo(latitude=32.8801, longitude=-117.234)
    _s         = _astral_sun(_loc.observer, date=_now, tzinfo=_local_tz)
    _time_str  = _now.strftime("%-I:%M %p")
    _dawn_str  = _s["dawn"].strftime("%-I:%M %p")
    _dusk_str  = _s["dusk"].strftime("%-I:%M %p")
    _tod_label = "After dark" if tod else "Daytime"
    _card_cls  = "time-card-night" if tod else "time-card-day"
    _main_cls  = "time-main-night" if tod else "time-main-day"

    st.markdown(
        f'<div class="{_card_cls}">'
        f'<div class="{_main_cls}">{_time_str} · {_tod_label}</div>'
        f'<div class="time-sub">Dawn {_dawn_str} &nbsp;·&nbsp; Dusk {_dusk_str}</div>'
        f'</div>',
        unsafe_allow_html=True,
    )

    origin      = st_searchbox(suggest_address, placeholder="Starting point…", key="orig_box", label="From")
    destination = st_searchbox(suggest_address, placeholder="Destination…",   key="dest_box", label="To")
    find_btn    = st.button("Find Routes", type="primary", use_container_width=True)

    st.markdown('<div class="sl">Map layers</div>', unsafe_allow_html=True)
    show_heatmap = st.checkbox("Crime hotspots", value=True, key="show_heatmap")

    if find_btn:
        if not origin or not destination:
            st.session_state.error = "Enter both a starting point and a destination."
        else:
            with st.spinner("Finding safest routes…"):
                try:
                    st.session_state.result      = pipeline.run(origin, destination)
                    st.session_state.error       = None
                    st.session_state.active_mode = "safest"
                except ValueError as e:
                    st.session_state.error  = str(e)
                    st.session_state.result = None
                except Exception as e:
                    st.session_state.error  = f"Something went wrong: {e}"
                    st.session_state.result = None

    if st.session_state.error:
        st.error(st.session_state.error)

    result = st.session_state.result
    if result:
        # ── Route cards ───────────────────────────────────────────────────────
        st.markdown('<div class="sl">Routes</div>', unsafe_allow_html=True)

        for mode, cfg in ROUTE_CFG.items():
            r              = result["routes"][mode]
            scores         = r.get("edge_scores", [])
            total_cost     = sum(e["safety_cost"] for e in scores)
            total_length   = sum(e["length_m"] for e in scores)
            safety_percent = f"{round((1 - (total_cost - total_length) / (4 * total_length)) * 100)}" if scores else "—"
            active         = st.session_state.active_mode == mode
            border         = f"border-color:{cfg['color']};" if active else ""
            bg             = "background:#eff6ff;" if active else ""

            st.markdown(
                f'<div class="rc {"active" if active else ""}" style="{border}{bg}">'
                f'<div class="rc-top">'
                f'<span class="rc-label">'
                f'<span class="rc-dot" style="background:{cfg["color"]}"></span>'
                f'{cfg["icon"]} {cfg["label"]}'
                f'</span>'
                f'<span class="rc-score">Score {safety_percent}</span>'
                f'</div>'
                f'<div class="rc-stats">'
                f'<span class="rc-val">{r["distance_mi"]} mi</span>'
                f'&nbsp;·&nbsp;'
                f'<span class="rc-val">{r["time_min"]} min</span>'
                f'&nbsp;walk</div></div>',
                unsafe_allow_html=True,
            )

            if st.button(
                f"{'✓ Selected' if active else 'Select'} — {cfg['icon']} {cfg['label']}",
                key=f"sel_{mode}",
                use_container_width=True,
                type="primary" if active else "secondary",
            ):
                st.session_state.active_mode = mode
                st.rerun()



# ── Hero text (night banner above SafePath) ───────────────────────────────────
if is_night_now() and not st.session_state.night_dismissed:
    msg_col, btn_col = st.columns([11, 1])
    with msg_col:
        st.warning("🌙 **It's nighttime** — we're prioritizing your safety. The **Safest** route is strongly recommended. Stay safe out there! 🛡️")
    with btn_col:
        st.markdown("<div style='padding-top:8px'>", unsafe_allow_html=True)
        if st.button("✕", key="dismiss_night"):
            st.session_state.night_dismissed = True
            st.rerun()
        st.markdown("</div>", unsafe_allow_html=True)
st.markdown(
    '<div style="padding: 28px 0 8px 0;">'
    '<div style="display:flex;align-items:center;gap:10px;margin-bottom:10px;">'
    '<div style="width:14px;height:14px;border-radius:50%;background:#2d7a5f;flex-shrink:0;"></div>'
    '<span style="font-size:48px;font-weight:900;color:#111827;letter-spacing:-1px;">SafePath</span>'
    '</div>'
    '<div style="font-size:28px;font-weight:700;color:#111827;letter-spacing:-0.5px;margin-bottom:8px;">'
    "Let's find a safer route in San Diego."
    '</div>'
    '<div style="font-size:17px;color:#111827;margin-top:8px;font-weight:500;">'
    'We score every street by crime, infrastructure (roads &amp; lighting), and walkability — then pick the route that keeps you safe.'
    '</div>'
    '</div>',
    unsafe_allow_html=True,
)

# ── Main area — tabs ───────────────────────────────────────────────────────────
tab_map, tab_compare = st.tabs(["🗺️ Map", "📊 Compare Routes"])

# ── Tab 1: Map ─────────────────────────────────────────────────────────────────
with tab_map:
    result      = st.session_state.result
    active_mode = st.session_state.active_mode

    center = [32.7157, -117.1611]
    zoom   = 13

    if result:
        oc     = result["origin_coords"]
        dc     = result["destination_coords"]
        center = [(oc[0] + dc[0]) / 2, (oc[1] + dc[1]) / 2]
        zoom   = 14

    # CartoDB Voyager — muted colors, not dark, not overly bright
    m = folium.Map(
        location=center,
        zoom_start=zoom,
        tiles="https://{s}.basemaps.cartocdn.com/rastertiles/voyager/{z}/{x}/{y}{r}.png",
        attr='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors &copy; <a href="https://carto.com/attributions">CARTO</a>',
    )

    if result:
        if st.session_state.get("show_heatmap", True):
            # Collect all route coords to build a bounding box
            _all_lats = [c[0] for mode in ROUTE_CFG for c in result["routes"][mode]["coords"]]
            _all_lngs = [c[1] for mode in ROUTE_CFG for c in result["routes"][mode]["coords"]]
            _buf = 0.01  # ~1 km padding
            _lat_min, _lat_max = min(_all_lats) - _buf, max(_all_lats) + _buf
            _lng_min, _lng_max = min(_all_lngs) - _buf, max(_all_lngs) + _buf
            heat_pts = [
                [la, lo] for la, lo in result["crime_pts"]
                if _lat_min <= la <= _lat_max and _lng_min <= lo <= _lng_max
            ]
            if heat_pts:
                import numpy as np

                # ~100m grid — only keep points in cells with 5+ incidents
                _cell_lat, _cell_lng = 0.0009, 0.001
                _counts = defaultdict(int)
                for la, lo in heat_pts:
                    _counts[(int(la / _cell_lat), int(lo / _cell_lng))] += 1
                _keep   = {c for c, n in _counts.items() if n >= 10}
                _pts    = [[la, lo] for la, lo in heat_pts
                           if (int(la / _cell_lat), int(lo / _cell_lng)) in _keep]

                if _pts:
                    # Percentile-based gradient: scale max intensity to p95 so
                    # a handful of extreme cells don't wash out the rest
                    _vals  = np.array([_counts[c] for c in _keep], dtype=float)
                    _p95   = float(np.percentile(_vals, 95))
                    HeatMap(
                        _pts,
                        radius=18, blur=22, min_opacity=0.25,
                        max_val=_p95,
                        gradient={
                            "0.0": "rgba(252,165,165,0)",
                            "0.4": "#fca5a5",
                            "0.65": "#ef4444",
                            "0.85": "#dc2626",
                            "1.0":  "#991b1b",
                        },
                    ).add_to(m)
                    folium.Element(
                        '<div style="position:fixed;bottom:24px;right:10px;z-index:1000;'
                        'background:white;padding:8px 12px;border-radius:8px;'
                        'border:1px solid #d1d5db;font-size:11px;font-family:sans-serif;'
                        'box-shadow:0 1px 4px rgba(0,0,0,0.1);">'
                        '<div style="font-weight:600;color:#374151;margin-bottom:5px;">Crime hotspots</div>'
                        '<div style="display:flex;align-items:center;gap:7px;">'
                        '<span style="display:inline-block;width:60px;height:8px;border-radius:4px;'
                        'background:linear-gradient(to right,#fca5a5,#ef4444,#991b1b);"></span>'
                        '<span style="color:#6b7280;">Low &rarr; High</span>'
                        '</div>'
                        '<div style="color:#9ca3af;font-size:10px;margin-top:4px;">Min 10 incidents · scaled to local area</div>'
                        '</div>'
                    ).add_to(m.get_root().html)

        all_coords = []

        for mode in [md for md in ROUTE_CFG if md != active_mode]:
            cfg    = ROUTE_CFG[mode]
            r      = result["routes"][mode]
            coords = r["coords"]
            all_coords.extend(coords)
            folium.PolyLine(
                coords,
                color=cfg["color"],
                weight=cfg["weight"],
                opacity=0.3,
                dash_array=cfg["dash"],
                tooltip=f"{cfg['icon']} {cfg['label']}: {r['distance_mi']} mi · {r['time_min']} min",
            ).add_to(m)

        cfg    = ROUTE_CFG[active_mode]
        r      = result["routes"][active_mode]
        coords = r["coords"]
        all_coords.extend(coords)
        folium.PolyLine(
            coords,
            color=cfg["color"],
            weight=cfg["weight"] + 2,
            opacity=1.0,
            dash_array=cfg["dash"],
            tooltip=f"{cfg['icon']} {cfg['label']}: {r['distance_mi']} mi · {r['time_min']} min",
        ).add_to(m)

        folium.CircleMarker(
            location=result["origin_coords"],
            radius=9, fill_color="#22c55e", color="#ffffff",
            weight=2, fill_opacity=1, tooltip="Start",
        ).add_to(m)
        folium.CircleMarker(
            location=result["destination_coords"],
            radius=9, fill_color="#ef4444", color="#ffffff",
            weight=2, fill_opacity=1, tooltip="Destination",
        ).add_to(m)

        if all_coords:
            lats = [c[0] for c in all_coords]
            lngs = [c[1] for c in all_coords]
            m.fit_bounds(
                [[min(lats), min(lngs)], [max(lats), max(lngs)]],
                padding_top_left=[50, 50],
                padding_bottom_right=[50, 50],
            )

    map_col, dir_col = st.columns([3, 1])

    with map_col:
        st_folium(
            m,
            use_container_width=True,
            height=700,
            returned_objects=[],
            key=f"map_{active_mode}_{st.session_state.get('show_heatmap', True)}",
        )

    with dir_col:
        if result:
            active_cfg = ROUTE_CFG[st.session_state.active_mode]
            st.markdown(
                f'<div class="sl">Directions — {active_cfg["icon"]} {active_cfg["label"]}</div>',
                unsafe_allow_html=True,
            )
            steps = result["routes"][st.session_state.active_mode].get("steps", [])
            html  = "".join(_step_html(i, s) for i, s in enumerate(steps))
            st.markdown(f'<div style="max-height:680px;overflow-y:auto;padding-right:4px;">{html}</div>', unsafe_allow_html=True)
        else:
            st.markdown(
                '<div style="padding-top:40px;text-align:center;color:#374151;font-size:15px;font-weight:500;">'
                '🗺️<br><br>Directions will appear here after you search a route.'
                '</div>',
                unsafe_allow_html=True,
            )


# ── Tab 2: Compare Routes ──────────────────────────────────────────────────────
with tab_compare:
    result = st.session_state.result

    if not result:
        st.markdown(
            '<div style="text-align:center;padding:60px 20px;color:#374151;">'
            '<div style="font-size:48px;margin-bottom:16px">🗺️</div>'
            '<div style="font-size:18px;font-weight:700;color:#111827;margin-bottom:8px">No routes yet</div>'
            '<div style="font-size:15px;font-weight:500;color:#374151">Search for an origin and destination to compare routes.</div>'
            '</div>',
            unsafe_allow_html=True,
        )
    else:
        st.markdown(
            '<div style="font-size:14px;font-weight:700;letter-spacing:.08em;'
            'text-transform:uppercase;color:#111827;margin-bottom:16px">'
            'All Routes — Side by Side</div>',
            unsafe_allow_html=True,
        )

        cols = st.columns(3)
        for (mode, cfg), col in zip(ROUTE_CFG.items(), cols):
            r              = result["routes"][mode]
            scores         = r.get("edge_scores", [])
            total_cost     = sum(e["safety_cost"] for e in scores)
            total_length   = sum(e["length_m"] for e in scores)
            safety_percent = round((1 - (total_cost - total_length) / (4 * total_length)) * 100)

            with col:
                st.markdown(
                    f'<div class="cmp-card" style="border:1.5px solid {cfg["color"]};">'
                    f'<div style="font-size:32px;margin-bottom:10px">{cfg["icon"]}</div>'
                    f'<div class="cmp-title">{cfg["label"]}</div>'
                    f'<div class="cmp-stat-label">Distance</div>'
                    f'<div class="cmp-stat-val">{r["distance_mi"]} mi</div>'
                    f'<div class="cmp-stat-label">Walk time</div>'
                    f'<div class="cmp-stat-val">{r["time_min"]} min</div>'
                    f'<div class="cmp-stat-label">Safety Percent</div>'
                    f'<div class="cmp-score-val" style="color:{cfg["color"]}">{safety_percent}%</div>'
                    f'</div>',
                    unsafe_allow_html=True,
                )

        st.markdown("<div style='margin-top:28px'></div>", unsafe_allow_html=True)
        st.markdown(
            '<div style="font-size:14px;font-weight:700;letter-spacing:.08em;'
            'text-transform:uppercase;color:#111827;margin-bottom:12px">'
            'Detailed Breakdown</div>',
            unsafe_allow_html=True,
        )

        import pandas as pd
        rows = []
        for mode, cfg in ROUTE_CFG.items():
            r      = result["routes"][mode]
            scores = r.get("edge_scores", [])
            avg       = sum(e["safety_score"]   for e in scores) / len(scores) if scores else 0
            avg_infra = sum(e["infrastructure"] for e in scores) / len(scores) if scores else 0
            avg_walk  = sum(e["walk_score"]     for e in scores) / len(scores) if scores else 0
            avg_crime = sum(e["crime_score"] for e in scores) / len(scores) if scores else 0
            rows.append({
                "Route":                             f"{cfg['icon']} {cfg['label']}",
                "Distance":                          f"{r['distance_mi']} mi",
                "Walk time":                         f"{r['time_min']} min",
                "Safety score":                      f"{avg:.2f}",
                "Crime safety score":                f"{avg_crime:.2f}",
                "Infrastructure (roads & lighting)": f"{avg_infra:.2f}",
                "Walk score":                        f"{avg_walk:.2f}",
            })

        df = pd.DataFrame(rows).set_index("Route")
        st.dataframe(df, use_container_width=True)
