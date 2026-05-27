from datetime import datetime
from astral import LocationInfo
from astral.sun import sun
from dateutil import tz


def is_night(lat: float = 32.8801, lng: float = -117.234) -> bool:
    """Return True if the current local time is after dusk or before dawn."""
    location   = LocationInfo(latitude=lat, longitude=lng)
    local_tz   = tz.tzlocal()
    s          = sun(location.observer, date=datetime.now(), tzinfo=local_tz)
    dawn_hour  = s["dawn"].hour + s["dawn"].minute / 60
    dusk_hour  = s["dusk"].hour + s["dusk"].minute / 60
    exact_hour = datetime.now().hour + datetime.now().minute / 60
    return exact_hour >= dusk_hour or exact_hour <= dawn_hour


def is_night_now() -> bool:
    """Convenience alias — always evaluates at call time, never stale."""
    return is_night()
