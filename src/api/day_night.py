from datetime import datetime
from suntime import Sun
from dateutil import tz


def is_night(lat: float = 32.8801, lng: float = -117.234) -> bool:
    """Return True if the current local time is after sunset or before sunrise."""
    sun = Sun(lat, lng)
    local_tz = tz.tzlocal()
    sunrise = sun.get_sunrise_time(datetime.now(), local_tz)
    sunset  = sun.get_sunset_time(datetime.now(), local_tz)
    sunrise_h  = sunrise.hour + sunrise.minute / 60
    sunset_h   = sunset.hour  + sunset.minute  / 60
    exact_hour = datetime.now().hour + datetime.now().minute / 60
    return exact_hour >= sunset_h or exact_hour <= sunrise_h


def is_night_now() -> bool:
    """Convenience alias — always evaluates at call time, never stale."""
    return is_night()
