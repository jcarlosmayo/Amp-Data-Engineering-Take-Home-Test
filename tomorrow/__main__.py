import logging
import sys

from tomorrow.api_client import RateLimitError
from tomorrow.config import LOCATIONS
from tomorrow.init_db import initialize_database
from tomorrow.pipeline import run_pipeline

# configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(name)s - %(message)s")
logger = logging.getLogger(__name__)


def main():
    """Main entry point for the tomorrow service."""
    try:
        logger.info("=" * 80)
        logger.info("TOMORROW.IO WEATHER DATA SERVICE STARTING")
        logger.info("=" * 80)
        logger.info(f"Will process {len(LOCATIONS)} locations")

        # Step 1: Initialize database tables if they don't exist
        logger.info("\nStep 1: Initializing database...")
        initialize_database()
        logger.info("✓ Database initialized")

        # Step 2: Run pipeline for all locations
        logger.info(f"\nStep 2: Running pipeline for {len(LOCATIONS)} locations...")

        total_records = 0
        total_history = 0
        total_forecast = 0
        failed_locations = []
        rate_limited = False

        for idx, (latitude, longitude) in enumerate(LOCATIONS, 1):
            if rate_limited:
                logger.warning(
                    f"\n  [{idx}/{len(LOCATIONS)}] Skipping location ({latitude}, {longitude}) — rate limit active"
                )
                failed_locations.append((latitude, longitude, "rate_limit"))
                continue

            logger.info(f"\n  [{idx}/{len(LOCATIONS)}] Processing location ({latitude}, {longitude})...")
            try:
                result = run_pipeline(latitude, longitude)
                total_records += result["records_processed"]
                total_history += result["history_count"]
                total_forecast += result["forecast_count"]
                logger.info(f"  ✓ Location ({latitude}, {longitude}) completed: {result['records_processed']} records")
            except RateLimitError as e:
                logger.warning(f"  ⏳ Location ({latitude}, {longitude}) skipped due to rate limit: {e}")
                failed_locations.append((latitude, longitude, "rate_limit"))
                rate_limited = True
                logger.warning("  ⏳ Skipping remaining locations — rate limit won't reset until next hour")
            except Exception as e:
                logger.error(f"  ✗ Location ({latitude}, {longitude}) failed: {e}")
                failed_locations.append((latitude, longitude, str(e)))

        if failed_locations:
            logger.warning(f"\n⚠ {len(failed_locations)}/{len(LOCATIONS)} locations failed (will retry next hour)")
            for lat, lon, reason in failed_locations:
                logger.warning(f"  - ({lat}, {lon}): {reason}")
        else:
            logger.info("\n✓ All locations processed successfully")

        # Print summary
        logger.info("\n" + "=" * 80)
        logger.info("SERVICE INITIALIZATION COMPLETE")
        logger.info("=" * 80)
        logger.info(f"Locations processed: {len(LOCATIONS)}")
        logger.info(f"Total records: {total_records}")
        logger.info(f"  - History records: {total_history}")
        logger.info(f"  - Forecast records: {total_forecast}")
        logger.info(f"  - Average per location: {total_records // len(LOCATIONS)}")
        logger.info("=" * 80)

        return 0

    except Exception as e:
        logger.error(f"\nService failed: {e}", exc_info=True)
        return 1


if __name__ == "__main__":
    sys.exit(main())
