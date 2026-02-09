"""Script to initialize the database tables."""
import logging
from tomorrow.db_client import DatabaseClient

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(name)s - %(message)s'
)
logger = logging.getLogger(__name__)


def initialize_database():
    """Initialize the database by creating necessary tables."""
    logger.info("Starting database initialization...")

    try:
        with DatabaseClient() as db:
            logger.info("Connected to database")
            db.create_tables()
            logger.info("Database tables initialized successfully!")

    except Exception as e:
        logger.error(f"Failed to initialize database: {e}", exc_info=True)
        raise


if __name__ == '__main__':
    initialize_database()
