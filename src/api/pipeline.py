from src.api import loader, day_night, geocoder, router


def run(origin_address: str, destination_address: str) -> dict:
    """Run the full SafePath pipeline and return everything the Streamlit UI needs."""
    rg        = loader.load_graph()        # RouteGraph — instant from @st.cache_resource
    crime_pts = loader.load_crime_points() # pre-split arrays
    is_night  = day_night.is_night_now()

    origin_coords = geocoder.address_to_latlng(origin_address)
    dest_coords   = geocoder.address_to_latlng(destination_address)

    route_data = router.get_routes(origin_coords, dest_coords, rg, is_night)
    routes_map = route_data["routes"]
    lt         = route_data["lt"]

    tod = "night" if is_night else "day"

    result = {
        "routes":             {},
        "is_night":           is_night,
        "origin_coords":      origin_coords,
        "destination_coords": dest_coords,
        "crime_pts":          crime_pts[tod],
    }

    for mode, path in routes_map.items():
        result["routes"][mode] = {
            "coords":      rg.path_coords(path),
            "edge_scores": rg.path_edge_scores(path, lt, is_night),
            "steps":       rg.path_steps(path),
            "distance_mi": round(rg.path_length_m(path) * 0.000621371, 2),
            "time_min":    rg.path_time_min(path),
        }

    return result
