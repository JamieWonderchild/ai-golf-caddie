import json
from unittest.mock import Mock, patch

import pytest

from golfcaddie.weather import fetch_current_wind, compute_components, summarize_wind, get_wind


@patch("httpx.Client")
def test_fetch_current_wind_ok(mock_client_cls):
    client = Mock()
    mock_client_cls.return_value.__enter__.return_value = client
    client.get.return_value.json.return_value = {
        "current": {"wind_speed_10m": 5.0, "wind_direction_10m": 270}
    }
    client.get.return_value.raise_for_status.return_value = None

    speed, direction = fetch_current_wind(51.5, -0.1)
    assert speed == 5.0
    assert direction == 270


@patch("httpx.Client")
def test_fetch_current_wind_fallback_to_cache(mock_client_cls):
    # First call populates cache
    client = Mock()
    mock_client_cls.return_value.__enter__.return_value = client
    client.get.return_value.json.return_value = {
        "current": {"wind_speed_10m": 4.0, "wind_direction_10m": 180}
    }
    client.get.return_value.raise_for_status.return_value = None
    s1, d1 = fetch_current_wind(40.0, -105.0)
    assert s1 == 4.0
    assert d1 == 180

    # Now force error and expect cached value
    client.get.side_effect = Exception("network")
    s2, d2 = fetch_current_wind(40.0, -105.0)
    assert s2 == 4.0 and d2 == 180


def test_compute_components_geometry():
    # Wind from west (270) blows toward east; target bearing north (0)
    head, cross = compute_components(5.0, 270, 0)
    # Crosswind should be negative (left-to-right)
    assert abs(head) < 1.0
    assert cross < -4.0


def test_get_wind_summary(monkeypatch):
    # stub fetch
    monkeypatch.setattr("golfcaddie.weather.fetch_current_wind", lambda lat, lon: (6.0, 180))
    w = get_wind(0.0, 0.0, 0)  # wind from south, toward north, target north → tailwind
    assert "mph" in w.summary
    assert "tailwind" in w.summary

