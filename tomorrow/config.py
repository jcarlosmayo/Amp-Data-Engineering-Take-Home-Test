"""Configuration module for Tomorrow.io API client."""

import os
from typing import Tuple

# API Configuration
API_KEY = os.environ["API_KEY"]
BASE_URL = "https://api.tomorrow.io/v4"

# API Endpoints
RECENT_HISTORY_URL = f"{BASE_URL}/weather/history/recent"
FORECAST_URL = f"{BASE_URL}/weather/forecast"

# All locations from ASSIGNMENT.md (South Texas, near Brownsville)
LOCATIONS = [
    (25.8600, -97.4200),
    (25.9000, -97.5200),
    (25.9000, -97.4800),
    (25.9000, -97.4400),
    (25.9000, -97.4000),
    (25.9200, -97.3800),
    (25.9400, -97.5400),
    (25.9400, -97.5200),
    (25.9400, -97.4800),
    (25.9400, -97.4400),
]

# First location (for backwards compatibility)
LATITUDE, LONGITUDE = LOCATIONS[0]

# API Parameters
UNITS = "metric"  # metric unit system
TIMESTEPS = "1h"  # hourly data

# Database Configuration
DB_HOST = os.getenv("PGHOST", "localhost")
DB_PORT = os.getenv("PGPORT", "5432")
DB_NAME = os.getenv("PGDATABASE", "tomorrow")
DB_USER = os.getenv("PGUSER", "postgres")
DB_PASSWORD = os.getenv("PGPASSWORD", "postgres")


def get_location() -> Tuple[float, float]:
    """Return the latitude and longitude as a tuple."""
    return (LATITUDE, LONGITUDE)


def get_db_connection_string() -> str:
    """Return PostgreSQL connection string."""
    return f"host={DB_HOST} port={DB_PORT} dbname={DB_NAME} user={DB_USER} password={DB_PASSWORD}"
