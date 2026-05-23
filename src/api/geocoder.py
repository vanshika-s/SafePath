from functools import lru_cache
from geopy.geocoders import Nominatim
from geopy.extra.rate_limiter import RateLimiter

_geolocator = Nominatim(user_agent="safepath-sd")
_geocode     = RateLimiter(_geolocator.geocode, min_delay_seconds=1)


@lru_cache(maxsize=512)
def address_to_latlng(address: str) -> tuple[float, float]:
    """Convert an address string to (lat, lng) via Nominatim, scoped to San Diego.

    Results are cached for the process lifetime so repeated searches for the
    same address skip the API call and rate-limiter delay entirely.
    """
    query = address if "san diego" in address.lower() else f"{address}, San Diego, CA"
    location = _geocode(query)
    if location is None:
        raise ValueError(f"Could not geocode address: {address!r}")
    return (location.latitude, location.longitude)
