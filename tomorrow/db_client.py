"""Database client for storing weather data in PostgreSQL."""
import logging
from typing import Dict, Any, List, Optional
import psycopg2
from psycopg2.extras import execute_batch
import json

from tomorrow.config import get_db_connection_string

logger = logging.getLogger(__name__)


class DatabaseClient:
    """Client for interacting with PostgreSQL database."""

    def __init__(self, connection_string: Optional[str] = None):
        """
        Initialize the database client.

        Args:
            connection_string: PostgreSQL connection string. If not provided, uses config defaults.
        """
        self.connection_string = connection_string or get_db_connection_string()
        self.conn = None

    def connect(self):
        """Establish connection to the database."""
        try:
            self.conn = psycopg2.connect(self.connection_string)
            logger.info("Successfully connected to PostgreSQL database")
        except psycopg2.Error as e:
            logger.error(f"Failed to connect to database: {e}")
            raise

    def close(self):
        """Close the database connection."""
        if self.conn:
            self.conn.close()
            logger.info("Database connection closed")

    def __enter__(self):
        """Context manager entry."""
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()

    def create_tables(self):
        """Create the weather_data table if it doesn't exist."""
        create_table_query = """
        CREATE TABLE IF NOT EXISTS weather_data (
            id SERIAL PRIMARY KEY,
            latitude DECIMAL(10, 6) NOT NULL,
            longitude DECIMAL(10, 6) NOT NULL,
            timestamp TIMESTAMP WITH TIME ZONE NOT NULL,
            data_type VARCHAR(50) NOT NULL,

            -- Temperature fields
            temperature DECIMAL(6, 2),
            temperature_apparent DECIMAL(6, 2),
            dew_point DECIMAL(6, 2),

            -- Wind fields
            wind_speed DECIMAL(6, 2),
            wind_direction DECIMAL(6, 2),
            wind_gust DECIMAL(6, 2),

            -- Humidity and pressure
            humidity DECIMAL(6, 2),
            pressure_surface_level DECIMAL(8, 2),
            pressure_sea_level DECIMAL(8, 2),
            altimeter_setting DECIMAL(8, 2),

            -- Cloud fields
            cloud_cover DECIMAL(6, 2),
            cloud_base DECIMAL(8, 2),
            cloud_ceiling DECIMAL(8, 2),

            -- Precipitation - rain
            rain_intensity DECIMAL(8, 4),
            rain_accumulation DECIMAL(8, 4),

            -- Precipitation - snow
            snow_intensity DECIMAL(8, 4),
            snow_accumulation DECIMAL(8, 4),
            snow_accumulation_lwe DECIMAL(8, 4),
            snow_depth DECIMAL(8, 2),

            -- Precipitation - sleet
            sleet_intensity DECIMAL(8, 4),
            sleet_accumulation DECIMAL(8, 4),
            sleet_accumulation_lwe DECIMAL(8, 4),

            -- Precipitation - freezing rain
            freezing_rain_intensity DECIMAL(8, 4),

            -- Precipitation - ice
            ice_accumulation DECIMAL(8, 4),
            ice_accumulation_lwe DECIMAL(8, 4),

            -- Precipitation probability
            precipitation_probability DECIMAL(6, 2),

            -- UV and visibility
            uv_index DECIMAL(6, 2),
            uv_health_concern DECIMAL(4, 2),
            visibility DECIMAL(8, 2),

            -- Other fields
            weather_code INTEGER,
            evapotranspiration DECIMAL(8, 4),

            -- Store complete raw data as JSONB for reference
            raw_data JSONB,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,

            UNIQUE(latitude, longitude, timestamp, data_type)
        );

        CREATE INDEX IF NOT EXISTS idx_weather_location
            ON weather_data(latitude, longitude);

        CREATE INDEX IF NOT EXISTS idx_weather_timestamp
            ON weather_data(timestamp);

        CREATE INDEX IF NOT EXISTS idx_weather_location_timestamp
            ON weather_data(latitude, longitude, timestamp);

        CREATE INDEX IF NOT EXISTS idx_weather_data_type
            ON weather_data(data_type);
        """

        try:
            with self.conn.cursor() as cursor:
                cursor.execute(create_table_query)
                self.conn.commit()
                logger.info("Weather data table created or already exists")
        except psycopg2.Error as e:
            logger.error(f"Failed to create tables: {e}")
            self.conn.rollback()
            raise

    def insert_weather_data(self, records: List[Dict[str, Any]]):
        """
        Insert weather data records into the database.

        Args:
            records: List of weather data dictionaries with flattened structure
        """
        if not records:
            logger.warning("No records to insert")
            return

        insert_query = """
        INSERT INTO weather_data (
            latitude, longitude, timestamp, data_type,
            temperature, temperature_apparent, dew_point,
            wind_speed, wind_direction, wind_gust,
            humidity, pressure_surface_level, pressure_sea_level, altimeter_setting,
            cloud_cover, cloud_base, cloud_ceiling,
            rain_intensity, rain_accumulation,
            snow_intensity, snow_accumulation, snow_accumulation_lwe, snow_depth,
            sleet_intensity, sleet_accumulation, sleet_accumulation_lwe,
            freezing_rain_intensity,
            ice_accumulation, ice_accumulation_lwe,
            precipitation_probability,
            uv_index, uv_health_concern, visibility,
            weather_code, evapotranspiration,
            raw_data
        ) VALUES (
            %(latitude)s, %(longitude)s, %(timestamp)s, %(data_type)s,
            %(temperature)s, %(temperature_apparent)s, %(dew_point)s,
            %(wind_speed)s, %(wind_direction)s, %(wind_gust)s,
            %(humidity)s, %(pressure_surface_level)s, %(pressure_sea_level)s, %(altimeter_setting)s,
            %(cloud_cover)s, %(cloud_base)s, %(cloud_ceiling)s,
            %(rain_intensity)s, %(rain_accumulation)s,
            %(snow_intensity)s, %(snow_accumulation)s, %(snow_accumulation_lwe)s, %(snow_depth)s,
            %(sleet_intensity)s, %(sleet_accumulation)s, %(sleet_accumulation_lwe)s,
            %(freezing_rain_intensity)s,
            %(ice_accumulation)s, %(ice_accumulation_lwe)s,
            %(precipitation_probability)s,
            %(uv_index)s, %(uv_health_concern)s, %(visibility)s,
            %(weather_code)s, %(evapotranspiration)s,
            %(raw_data)s
        )
        ON CONFLICT (latitude, longitude, timestamp, data_type)
        DO UPDATE SET
            temperature = EXCLUDED.temperature,
            temperature_apparent = EXCLUDED.temperature_apparent,
            dew_point = EXCLUDED.dew_point,
            wind_speed = EXCLUDED.wind_speed,
            wind_direction = EXCLUDED.wind_direction,
            wind_gust = EXCLUDED.wind_gust,
            humidity = EXCLUDED.humidity,
            pressure_surface_level = EXCLUDED.pressure_surface_level,
            pressure_sea_level = EXCLUDED.pressure_sea_level,
            altimeter_setting = EXCLUDED.altimeter_setting,
            cloud_cover = EXCLUDED.cloud_cover,
            cloud_base = EXCLUDED.cloud_base,
            cloud_ceiling = EXCLUDED.cloud_ceiling,
            rain_intensity = EXCLUDED.rain_intensity,
            rain_accumulation = EXCLUDED.rain_accumulation,
            snow_intensity = EXCLUDED.snow_intensity,
            snow_accumulation = EXCLUDED.snow_accumulation,
            snow_accumulation_lwe = EXCLUDED.snow_accumulation_lwe,
            snow_depth = EXCLUDED.snow_depth,
            sleet_intensity = EXCLUDED.sleet_intensity,
            sleet_accumulation = EXCLUDED.sleet_accumulation,
            sleet_accumulation_lwe = EXCLUDED.sleet_accumulation_lwe,
            freezing_rain_intensity = EXCLUDED.freezing_rain_intensity,
            ice_accumulation = EXCLUDED.ice_accumulation,
            ice_accumulation_lwe = EXCLUDED.ice_accumulation_lwe,
            precipitation_probability = EXCLUDED.precipitation_probability,
            uv_index = EXCLUDED.uv_index,
            uv_health_concern = EXCLUDED.uv_health_concern,
            visibility = EXCLUDED.visibility,
            weather_code = EXCLUDED.weather_code,
            evapotranspiration = EXCLUDED.evapotranspiration,
            raw_data = EXCLUDED.raw_data,
            created_at = CURRENT_TIMESTAMP;
        """

        try:
            with self.conn.cursor() as cursor:
                # Convert raw_data dict to JSON string for psycopg2
                for record in records:
                    if 'raw_data' in record and record['raw_data'] is not None:
                        record['raw_data'] = json.dumps(record['raw_data'])

                execute_batch(cursor, insert_query, records)
                self.conn.commit()
                logger.info(f"Successfully inserted/updated {len(records)} weather records")
        except psycopg2.Error as e:
            logger.error(f"Failed to insert weather data: {e}")
            self.conn.rollback()
            raise

    def get_latest_temperature_and_wind(self) -> List[Dict[str, Any]]:
        """
        Get the latest temperature and wind speed for each location.

        Returns:
            List of dictionaries with latitude, longitude, temperature, and wind_speed
        """
        query = """
        SELECT DISTINCT ON (latitude, longitude)
            latitude,
            longitude,
            temperature,
            wind_speed,
            timestamp
        FROM weather_data
        ORDER BY latitude, longitude, timestamp DESC;
        """

        try:
            with self.conn.cursor() as cursor:
                cursor.execute(query)
                columns = [desc[0] for desc in cursor.description]
                results = [dict(zip(columns, row)) for row in cursor.fetchall()]
                logger.info(f"Retrieved latest data for {len(results)} locations")
                return results
        except psycopg2.Error as e:
            logger.error(f"Failed to query latest data: {e}")
            raise

    def get_hourly_timeseries(
        self,
        latitude: float,
        longitude: float,
        hours_past: int = 24,
        hours_future: int = 120
    ) -> List[Dict[str, Any]]:
        """
        Get hourly time series data for a specific location.

        Args:
            latitude: Location latitude
            longitude: Location longitude
            hours_past: Number of hours in the past (default 24 = 1 day)
            hours_future: Number of hours in the future (default 120 = 5 days)

        Returns:
            List of weather data records ordered by timestamp
        """
        query = """
        SELECT
            timestamp,
            temperature,
            wind_speed,
            humidity,
            precipitation,
            cloud_cover,
            pressure_surface_level,
            visibility,
            uv_index,
            weather_code,
            data_type
        FROM weather_data
        WHERE
            latitude = %s
            AND longitude = %s
            AND timestamp >= NOW() - INTERVAL '%s hours'
            AND timestamp <= NOW() + INTERVAL '%s hours'
        ORDER BY timestamp;
        """

        try:
            with self.conn.cursor() as cursor:
                cursor.execute(query, (latitude, longitude, hours_past, hours_future))
                columns = [desc[0] for desc in cursor.description]
                results = [dict(zip(columns, row)) for row in cursor.fetchall()]
                logger.info(f"Retrieved {len(results)} hourly records for location ({latitude}, {longitude})")
                return results
        except psycopg2.Error as e:
            logger.error(f"Failed to query time series data: {e}")
            raise
