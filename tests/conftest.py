"""Shared fixtures for the test suite."""

import json
from pathlib import Path

import pytest

FIXTURES_DIR = Path(__file__).parent / "fixtures"


@pytest.fixture
def sample_history_response():
    """A real Tomorrow.io recent history API response loaded from fixture file."""
    with open(FIXTURES_DIR / "recent_history.json") as f:
        return json.load(f)


@pytest.fixture
def sample_forecast_response():
    """A real Tomorrow.io forecast API response loaded from fixture file."""
    with open(FIXTURES_DIR / "forecast.json") as f:
        return json.load(f)


@pytest.fixture
def sample_flat_record():
    """A single flattened record matching the output shape of flatten_weather_data."""
    return {
        "latitude": 25.86,
        "longitude": -97.42,
        "timestamp": "2023-01-25T10:00:00Z",
        "data_type": "forecast",
        "temperature": 5.13,
        "temperature_apparent": 5.13,
        "dew_point": 2.81,
        "wind_speed": 2.5,
        "wind_direction": 314.13,
        "wind_gust": 9.69,
        "humidity": 85,
        "pressure_surface_level": 998.13,
        "pressure_sea_level": None,
        "altimeter_setting": None,
        "cloud_cover": 9,
        "cloud_base": None,
        "cloud_ceiling": None,
        "rain_intensity": 0,
        "rain_accumulation": 0,
        "snow_intensity": 0,
        "snow_accumulation": 0,
        "snow_accumulation_lwe": 0,
        "snow_depth": 0,
        "sleet_intensity": 0,
        "sleet_accumulation": 0,
        "sleet_accumulation_lwe": 0,
        "freezing_rain_intensity": 0,
        "ice_accumulation": 0,
        "ice_accumulation_lwe": 0,
        "precipitation_probability": 0,
        "uv_index": 0,
        "uv_health_concern": 0,
        "visibility": 15.9,
        "weather_code": 1000,
        "evapotranspiration": 0.035,
        "raw_data": {"temperature": 5.13, "windSpeed": 2.5},
    }
