"""Data processing module for flattening Tomorrow.io API responses."""
import logging
from typing import Dict, Any, List
from datetime import datetime

logger = logging.getLogger(__name__)


def flatten_weather_data(
    api_response: Dict[str, Any],
    data_type: str,
    latitude: float,
    longitude: float
) -> List[Dict[str, Any]]:
    """
    Flatten Tomorrow.io API response into a list of database records.

    Args:
        api_response: Raw JSON response from Tomorrow.io API
        data_type: Type of data ('recent_history' or 'forecast')
        latitude: Location latitude
        longitude: Location longitude

    Returns:
        List of flattened weather data records ready for database insertion
    """
    records = []

    try:
        # Tomorrow.io API structure: timelines.hourly[]
        timelines_obj = api_response.get('timelines', {})
        hourly_data = timelines_obj.get('hourly', [])

        if not hourly_data:
            logger.warning(f"No hourly data found in API response for {data_type}")
            return records

        for data_point in hourly_data:
            timestamp = data_point.get('time')
            values = data_point.get('values', {})

            if not timestamp:
                logger.warning("Skipping data point without timestamp")
                continue

            # Create flattened record with all available fields
            record = {
                'latitude': latitude,
                'longitude': longitude,
                'timestamp': timestamp,
                'data_type': data_type,

                # Temperature fields
                'temperature': values.get('temperature'),
                'temperature_apparent': values.get('temperatureApparent'),
                'dew_point': values.get('dewPoint'),

                # Wind fields
                'wind_speed': values.get('windSpeed'),
                'wind_direction': values.get('windDirection'),
                'wind_gust': values.get('windGust'),

                # Humidity and pressure
                'humidity': values.get('humidity'),
                'pressure_surface_level': values.get('pressureSurfaceLevel'),
                'pressure_sea_level': values.get('pressureSeaLevel'),
                'altimeter_setting': values.get('altimeterSetting'),

                # Cloud fields
                'cloud_cover': values.get('cloudCover'),
                'cloud_base': values.get('cloudBase'),
                'cloud_ceiling': values.get('cloudCeiling'),

                # Precipitation - rain
                'rain_intensity': values.get('rainIntensity'),
                'rain_accumulation': values.get('rainAccumulation'),

                # Precipitation - snow
                'snow_intensity': values.get('snowIntensity'),
                'snow_accumulation': values.get('snowAccumulation'),
                'snow_accumulation_lwe': values.get('snowAccumulationLwe'),
                'snow_depth': values.get('snowDepth'),

                # Precipitation - sleet
                'sleet_intensity': values.get('sleetIntensity'),
                'sleet_accumulation': values.get('sleetAccumulation'),
                'sleet_accumulation_lwe': values.get('sleetAccumulationLwe'),

                # Precipitation - freezing rain
                'freezing_rain_intensity': values.get('freezingRainIntensity'),

                # Precipitation - ice
                'ice_accumulation': values.get('iceAccumulation'),
                'ice_accumulation_lwe': values.get('iceAccumulationLwe'),

                # Precipitation probability
                'precipitation_probability': values.get('precipitationProbability'),

                # UV and visibility
                'uv_index': values.get('uvIndex'),
                'uv_health_concern': values.get('uvHealthConcern'),
                'visibility': values.get('visibility'),

                # Other fields
                'weather_code': values.get('weatherCode'),
                'evapotranspiration': values.get('evapotranspiration'),

                # Store complete values object as JSONB for reference
                'raw_data': values
            }

            records.append(record)

        logger.info(f"Flattened {len(records)} records from {data_type} API response")

    except Exception as e:
        logger.error(f"Error flattening weather data: {e}", exc_info=True)
        raise

    return records


def process_api_responses(
    recent_history: Dict[str, Any],
    forecast: Dict[str, Any],
    latitude: float,
    longitude: float
) -> Dict[str, List[Dict[str, Any]]]:
    """
    Process both API responses and flatten them into database records.

    Args:
        recent_history: Response from /weather/history/recent endpoint
        forecast: Response from /weather/forecast endpoint
        latitude: Location latitude
        longitude: Location longitude

    Returns:
        Dictionary with 'recent_history' and 'forecast' keys containing flattened records
    """
    logger.info(f"Processing API responses for location ({latitude}, {longitude})")

    history_records = flatten_weather_data(
        recent_history,
        data_type='recent_history',
        latitude=latitude,
        longitude=longitude
    )

    forecast_records = flatten_weather_data(
        forecast,
        data_type='forecast',
        latitude=latitude,
        longitude=longitude
    )

    logger.info(
        f"Processed {len(history_records)} history records and "
        f"{len(forecast_records)} forecast records"
    )

    return {
        'recent_history': history_records,
        'forecast': forecast_records
    }


def combine_records(processed_data: Dict[str, List[Dict[str, Any]]]) -> List[Dict[str, Any]]:
    """
    Combine history and forecast records into a single list.

    Args:
        processed_data: Dictionary with 'recent_history' and 'forecast' keys

    Returns:
        Combined list of all weather records
    """
    all_records = []
    all_records.extend(processed_data.get('recent_history', []))
    all_records.extend(processed_data.get('forecast', []))

    logger.info(f"Combined {len(all_records)} total records")
    return all_records
