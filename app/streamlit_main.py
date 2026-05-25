import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from html import escape
import requests as _requests
import streamlit as st
import folium
from folium.plugins import HeatMap
from streamlit_folium import st_folium
from streamlit_searchbox import st_searchbox

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
    font-size: 13px;
    font-weight: 600;
    color: #111827;
}
.rc-dot {
    width: 11px;
    height: 11px;
    border-radius: 50%;
    display: inline-block;
    flex-shrink: 0;
}
.rc-score {
    font-size: 11px;
    background: #e5e7eb;
    padding: 2px 8px;
    border-radius: 8px;
    color: #4b5563;
}
.rc-stats { font-size: 12px; color: #6b7280; }
.rc-val   { color: #111827; font-weight: 500; }

/* Directions */
.dir-step {
    display: flex;
    gap: 12px;
    align-items: flex-start;
    padding: 8px 0;
    border-bottom: 1px solid #e5e7eb;
}
.dir-step:last-child { border-bottom: none; }
.dir-icon {
    width: 28px;
    height: 28px;
    background: #e5e7eb;
    border-radius: 50%;
    display: inline-flex;
    align-items: center;
    justify-content: center;
    font-size: 13px;
    flex-shrink: 0;
}
.dir-icon.dest { background: #fee2e2; border: 1px solid #ef4444; }
.dir-body  { flex: 1; min-width: 0; }
.dir-num   { font-size: 10px; color: #9ca3af; font-weight: 600; margin-bottom: 2px; }
.dir-instr { font-size: 12px; color: #111827; line-height: 1.4; font-weight: 500; }
.dir-dist  { font-size: 11px; color: #6b7280; margin-top: 2px; }

/* Section labels */
.sl {
    font-size: 10px;
    font-weight: 600;
    letter-spacing: .08em;
    text-transform: uppercase;
    color: #9ca3af;
    margin: 12px 0 8px 0;
}

/* Brand */
.brand      { display: flex; align-items: center; gap: 10px; margin-bottom: 4px; }
.brand-dot  { width: 10px; height: 10px; border-radius: 50%; background: #10b981; flex-shrink: 0; }
.brand-name { font-size: 17px; font-weight: 700; color: #111827; }
.tod        { font-size: 12px; color: #6b7280; margin-bottom: 4px; }

/* Compare cards */
.cmp-card {
    border-radius: 12px;
    padding: 20px 16px;
    background: #f9fafb;
    text-align: center;
    height: 100%;
}
.cmp-stat-label { color: #6b7280; font-size: 11px; margin-bottom: 2px; }
.cmp-stat-val   { color: #111827; font-size: 22px; font-weight: 600; margin-bottom: 14px; }
.cmp-score-val  { font-size: 22px; font-weight: 600; margin-bottom: 4px; }
.cmp-title      { font-size: 16px; font-weight: 700; color: #111827; margin-bottom: 18px; }

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
if "night_alerted"    not in st.session_state: st.session_state.night_alerted    = False

# ── Night alert (once per session) ────────────────────────────────────────────
if is_night_now() and not st.session_state.night_alerted:
    st.toast("🌙 It's nighttime — we're routing you along the safest streets. Stay safe!", icon="🛡️")
    st.session_state.night_alerted = True


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
    tod      = is_night_now()
    tod_icon = "🌙" if tod else "☀️"
    tod_text = "Night mode — elevated crime weights" if tod else "Day mode"

    st.markdown(
        f'<div class="brand"><div class="brand-dot"></div>'
        f'<span class="brand-name">SafePath</span></div>'
        f'<div class="tod">{tod_icon} {tod_text}</div>'
        f'<div class="sl">Route</div>',
        unsafe_allow_html=True,
    )

    origin      = st_searchbox(suggest_address, placeholder="Starting point…",  key="orig_box", label="From")
    destination = st_searchbox(suggest_address, placeholder="Destination…",      key="dest_box", label="To")
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
            r      = result["routes"][mode]
            scores = r.get("edge_scores", [])
            avg    = f"{sum(e['safety_score'] for e in scores)/len(scores):.2f}" if scores else "—"
            active = st.session_state.active_mode == mode
            border = f"border-color:{cfg['color']};" if active else ""
            bg     = "background:#eff6ff;" if active else ""

            st.markdown(
                f'<div class="rc {"active" if active else ""}" style="{border}{bg}">'
                f'<div class="rc-top">'
                f'<span class="rc-label">'
                f'<span class="rc-dot" style="background:{cfg["color"]}"></span>'
                f'{cfg["icon"]} {cfg["label"]}'
                f'</span>'
                f'<span class="rc-score">Score {avg}</span>'
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



# ── Hero text ─────────────────────────────────────────────────────────────────
st.markdown(
    '<div style="padding: 28px 0 8px 0;">'
    '<div style="font-size:28px;font-weight:700;color:#111827;letter-spacing:-0.5px;">'
    "Let's find a safer route in San Diego."
    '</div>'
    '<div style="font-size:14px;color:#6b7280;margin-top:6px;">'
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
            heat_pts = [[la, lo] for la, lo in result["crime_pts"]]
            if heat_pts:
                HeatMap(
                    heat_pts,
                    radius=18, blur=22, min_opacity=0.2,
                    gradient={"0": "rgba(0,0,0,0)", "0.4": "#fca5a5", "0.7": "#ef4444", "1.0": "#991b1b"},
                ).add_to(m)

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
            m.fit_bounds(
                all_coords,
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
            st.markdown(f'<div style="max-height:680px;overflow-y:auto;">{html}</div>', unsafe_allow_html=True)
        else:
            st.markdown(
                '<div style="padding-top:40px;text-align:center;color:#9ca3af;font-size:13px;">'
                '🗺️<br><br>Directions will appear here after you search a route.'
                '</div>',
                unsafe_allow_html=True,
            )


# ── Tab 2: Compare Routes ──────────────────────────────────────────────────────
with tab_compare:
    result = st.session_state.result

    if not result:
        st.markdown(
            '<div style="text-align:center;padding:60px 20px;color:#6b7280;">'
            '<div style="font-size:48px;margin-bottom:16px">🗺️</div>'
            '<div style="font-size:16px;font-weight:600;color:#374151;margin-bottom:8px">No routes yet</div>'
            '<div style="font-size:13px">Search for an origin and destination to compare routes.</div>'
            '</div>',
            unsafe_allow_html=True,
        )
    else:
        st.markdown(
            '<div style="font-size:11px;font-weight:600;letter-spacing:.08em;'
            'text-transform:uppercase;color:#9ca3af;margin-bottom:16px">'
            'All Routes — Side by Side</div>',
            unsafe_allow_html=True,
        )

        cols = st.columns(3)
        for (mode, cfg), col in zip(ROUTE_CFG.items(), cols):
            r      = result["routes"][mode]
            scores = r.get("edge_scores", [])
            avg    = sum(e["safety_score"] for e in scores) / len(scores) if scores else 0

            with col:
                st.markdown(
                    f'<div class="cmp-card" style="border:1.5px solid {cfg["color"]};">'
                    f'<div style="font-size:32px;margin-bottom:10px">{cfg["icon"]}</div>'
                    f'<div class="cmp-title">{cfg["label"]}</div>'
                    f'<div class="cmp-stat-label">Distance</div>'
                    f'<div class="cmp-stat-val">{r["distance_mi"]} mi</div>'
                    f'<div class="cmp-stat-label">Walk time</div>'
                    f'<div class="cmp-stat-val">{r["time_min"]} min</div>'
                    f'<div class="cmp-stat-label">Avg safety score</div>'
                    f'<div class="cmp-score-val" style="color:{cfg["color"]}">{avg:.2f}</div>'
                    f'</div>',
                    unsafe_allow_html=True,
                )

        st.markdown("<div style='margin-top:28px'></div>", unsafe_allow_html=True)
        st.markdown(
            '<div style="font-size:11px;font-weight:600;letter-spacing:.08em;'
            'text-transform:uppercase;color:#9ca3af;margin-bottom:12px">'
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
            rows.append({
                "Route":          f"{cfg['icon']} {cfg['label']}",
                "Distance":       f"{r['distance_mi']} mi",
                "Walk time":      f"{r['time_min']} min",
                "Safety score":   f"{avg:.2f}",
                "Infrastructure (roads & lighting)": f"{avg_infra:.2f}",
                "Walk score":     f"{avg_walk:.2f}",
            })

        df = pd.DataFrame(rows).set_index("Route")
        st.dataframe(df, use_container_width=True)
