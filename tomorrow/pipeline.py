"""Complete pipeline to fetch, flatten, and load weather data."""

import logging

from tomorrow.api_client import fetch_all_data
from tomorrow.config import LATITUDE, LONGITUDE
from tomorrow.data_processor import combine_records, process_api_responses
from tomorrow.db_client import DatabaseClient

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(name)s - %(message)s")
logger = logging.getLogger(__name__)


def run_pipeline(latitude: float = LATITUDE, longitude: float = LONGITUDE):
    """
    Run the complete data pipeline: fetch -> flatten -> load.

    Args:
        latitude: Location latitude
        longitude: Location longitude
    """
    logger.info("=" * 80)
    logger.info("STARTING WEATHER DATA PIPELINE")
    logger.info("=" * 80)
    logger.info(f"Target location: ({latitude}, {longitude})")

    try:
        # Step 1: Fetch data from API
        logger.info("Step 1: Fetching data from Tomorrow.io API...")
        api_data = fetch_all_data(latitude, longitude)
        logger.info("✓ API data fetched successfully")

        # Step 2: Flatten the JSON responses
        logger.info("Step 2: Flattening JSON responses...")
        processed_data = process_api_responses(
            recent_history=api_data["recent_history"],
            forecast=api_data["forecast"],
            latitude=latitude,
            longitude=longitude,
        )
        all_records = combine_records(processed_data)
        logger.info(f"✓ Flattened {len(all_records)} total records")

        # Step 3: Load into database
        logger.info("Step 3: Loading data into PostgreSQL...")
        with DatabaseClient() as db:
            db.insert_weather_data(all_records)
        logger.info("✓ Data loaded successfully")

        logger.info("=" * 80)
        logger.info("PIPELINE COMPLETED SUCCESSFULLY!")
        logger.info("=" * 80)

        return {
            "success": True,
            "records_processed": len(all_records),
            "history_count": len(processed_data["recent_history"]),
            "forecast_count": len(processed_data["forecast"]),
        }

    except Exception as e:
        logger.error(f"Pipeline failed: {e}", exc_info=True)
        raise


if __name__ == "__main__":
    result = run_pipeline()
    print("\nPipeline Summary:")
    print(f"  - Total records: {result['records_processed']}")
    print(f"  - History records: {result['history_count']}")
    print(f"  - Forecast records: {result['forecast_count']}")
