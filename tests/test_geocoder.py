"""Tests for geocoder.py — mocks Nominatim so no real HTTP calls are made."""
import pytest
from unittest.mock import patch, MagicMock

from src.api.geocoder import address_to_latlng


def _make_location(lat=32.8, lng=-117.2):
    loc = MagicMock()
    loc.latitude = lat
    loc.longitude = lng
    return loc


class TestAddressToLatLng:
    def setup_method(self):
        # Clear the lru_cache between tests so mocks work correctly
        address_to_latlng.cache_clear()

    def test_returns_lat_lng_tuple(self):
        with patch("src.api.geocoder._geocode", return_value=_make_location(32.8801, -117.234)):
            result = address_to_latlng("UCSD")
        assert isinstance(result, tuple)
        assert len(result) == 2

    def test_correct_coordinates(self):
        with patch("src.api.geocoder._geocode", return_value=_make_location(32.71, -117.16)):
            lat, lng = address_to_latlng("Gaslamp Quarter")
        assert abs(lat - 32.71) < 0.01
        assert abs(lng - (-117.16)) < 0.01

    def test_strips_comma_suffix(self):
        """Nominatim sometimes returns long formatted strings — we strip after the first comma."""
        with patch("src.api.geocoder._geocode") as mock_geocode:
            mock_geocode.return_value = _make_location(32.8, -117.2)
            address_to_latlng("UCSD, La Jolla, San Diego, CA")
            called_with = mock_geocode.call_args[0][0]
            assert called_with == "UCSD, San Diego, CA"

    def test_raises_for_not_found(self):
        with patch("src.api.geocoder._geocode", return_value=None):
            with pytest.raises(ValueError, match="Could not find"):
                address_to_latlng("NotARealPlaceXYZ")

    def test_result_is_cached(self):
        with patch("src.api.geocoder._geocode", return_value=_make_location()) as mock:
            address_to_latlng("Balboa Park")
            address_to_latlng("Balboa Park")
            assert mock.call_count == 1
