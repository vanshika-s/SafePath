from datetime import datetime
from zoneinfo import ZoneInfo

from astral import LocationInfo
from astral.sun import sun

# SafePath only covers San Diego, so day/night is always evaluated in
# San Diego's local time — independent of whatever timezone the server runs in.
_SD_TZ = ZoneInfo("America/Los_Angeles")


def is_night(lat: float = 32.8801, lng: float = -117.234) -> bool:
    """Return True if it is currently after dusk or before dawn in San Diego.

    Compares timezone-aware datetimes directly (not extracted hour floats), so
    it stays correct no matter what timezone the host machine is set to.
    """
    location = LocationInfo(latitude=lat, longitude=lng)
    now      = datetime.now(_SD_TZ)
    s        = sun(location.observer, date=now.date(), tzinfo=_SD_TZ)
    return now < s["dawn"] or now > s["dusk"]


def is_night_now() -> bool:
    """Convenience alias — always evaluates at call time, never stale."""
    return is_night()
