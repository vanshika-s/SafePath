from functools import lru_cache
from geopy.geocoders import Nominatim
from geopy.extra.rate_limiter import RateLimiter

_geolocator = Nominatim(user_agent="safepath-sd")
_geocode     = RateLimiter(_geolocator.geocode, min_delay_seconds=1)


@lru_cache(maxsize=512)
def address_to_latlng(address: str) -> tuple[float, float]:
    """Convert an address string to (lat, lng) via Nominatim, scoped to San Diego.

    Always uses only the first part of the address before any comma to avoid
    Nominatim returning a full formatted address string that fails on re-geocoding.
    Results are cached for the process lifetime so repeated searches skip the
    API call and rate-limiter delay entirely.
    """
    # Take only the first component before any comma — strips city/state/zip
    # that Nominatim may have appended in a previous call or that the user included
    clean = address.split(",")[0].strip()
    query = f"{clean}, San Diego, CA"

    location = _geocode(query)
    if location is None:
        raise ValueError(
            f"Could not find '{clean}' in San Diego. "
            f"Try being more specific, e.g. 'UCSD Health La Jolla'."
        )
    return (location.latitude, location.longitude)
