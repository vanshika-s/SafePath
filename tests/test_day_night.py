"""Tests for day_night.py — verifies correct SD timezone behaviour on any server."""
import pytest
from datetime import datetime
from unittest.mock import patch
from zoneinfo import ZoneInfo

from src.api.day_night import is_night, is_night_now

_SD_TZ = ZoneInfo("America/Los_Angeles")


def _mock_now(hour: int, minute: int = 0):
    """Return a mock datetime pinned to a specific San Diego local time today."""
    from astral import LocationInfo
    from astral.sun import sun
    real_now = datetime.now(_SD_TZ)
    s = sun(LocationInfo(latitude=32.8801, longitude=-117.234).observer,
            date=real_now.date(), tzinfo=_SD_TZ)
    # Use the real date but override the hour so tests are stable
    return real_now.replace(hour=hour, minute=minute, second=0, microsecond=0)


class TestIsNight:
    def test_midday_is_not_night(self):
        with patch("src.api.day_night.datetime") as m:
            m.now.return_value = _mock_now(12)
            assert is_night() is False

    def test_midnight_is_night(self):
        with patch("src.api.day_night.datetime") as m:
            m.now.return_value = _mock_now(0)
            assert is_night() is True

    def test_3am_is_night(self):
        with patch("src.api.day_night.datetime") as m:
            m.now.return_value = _mock_now(3)
            assert is_night() is True

    def test_9am_is_not_night(self):
        with patch("src.api.day_night.datetime") as m:
            m.now.return_value = _mock_now(9)
            assert is_night() is False

    def test_returns_bool(self):
        assert isinstance(is_night(), bool)

    def test_is_night_now_matches_is_night(self):
        assert is_night_now() == is_night()
