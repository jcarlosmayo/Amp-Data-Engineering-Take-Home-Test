"""API client for Tomorrow.io weather data."""
import logging
import time
from typing import Dict, Any, Optional
import requests
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
    before_sleep_log
)

from tomorrow.config import (
    API_KEY,
    RECENT_HISTORY_URL,
    FORECAST_URL,
    LATITUDE,
    LONGITUDE,
    UNITS,
    TIMESTEPS
)

logger = logging.getLogger(__name__)


class RateLimitError(Exception):
    """Raised when API rate limit is exceeded."""
    def __init__(self, message: str, retry_after: int = None):
        super().__init__(message)
        self.retry_after = retry_after


class TomorrowIOClient:
    """Client for interacting with Tomorrow.io API."""

    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize the Tomorrow.io API client.

        Args:
            api_key: API key for Tomorrow.io. If not provided, uses config default.
        """
        self.api_key = api_key or API_KEY
        self.session = requests.Session()

    @retry(
        retry=retry_if_exception_type(RateLimitError),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=60, max=300),
        before_sleep=before_sleep_log(logger, logging.WARNING)
    )
    def _make_request(self, url: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Make a GET request to the Tomorrow.io API with automatic retry on rate limits.

        Implements exponential backoff retry logic:
        - Retries up to 3 times on rate limit errors (429)
        - Wait time: 60s, 120s, 240s (exponential backoff)
        - Maximum wait: 5 minutes (300s)

        Args:
            url: The API endpoint URL
            params: Query parameters for the request

        Returns:
            JSON response as a dictionary

        Raises:
            RateLimitError: If rate limit exceeded after all retries
            requests.exceptions.RequestException: If other request errors occur
        """
        params['apikey'] = self.api_key

        logger.info(f"Making request to {url}")
        logger.debug(f"Parameters: {params}")

        try:
            response = self.session.get(url, params=params, timeout=30)

            # Check for rate limit (429 Too Many Requests)
            if response.status_code == 429:
                retry_after = int(response.headers.get('Retry-After', 3600))
                logger.warning(
                    f"⚠️  Rate limit exceeded (429). "
                    f"API requests: 25/hour limit reached. "
                    f"Retry after: {retry_after}s"
                )
                raise RateLimitError(
                    f"Tomorrow.io API rate limit exceeded. Retry after {retry_after} seconds.",
                    retry_after=retry_after
                )

            # Raise HTTPError for other 4xx/5xx status codes
            response.raise_for_status()

            data = response.json()
            logger.info(f"✓ Successfully received data from {url}")

            return data

        except requests.exceptions.Timeout:
            logger.error(f"Request timeout for {url}")
            raise
        except requests.exceptions.ConnectionError as e:
            logger.error(f"Connection error for {url}: {e}")
            raise
        except RateLimitError:
            # Re-raise to trigger retry logic
            raise
        except requests.exceptions.HTTPError as e:
            logger.error(f"HTTP error for {url}: {e}")
            raise
        except requests.exceptions.RequestException as e:
            logger.error(f"Request failed for {url}: {e}")
            raise

    def get_recent_history(
        self,
        latitude: float = LATITUDE,
        longitude: float = LONGITUDE,
        units: str = UNITS,
        timesteps: str = TIMESTEPS
    ) -> Dict[str, Any]:
        """
        Fetch recent weather history for a location.

        Args:
            latitude: Latitude of the location
            longitude: Longitude of the location
            units: Unit system ('metric' or 'imperial')
            timesteps: Time resolution ('1h' for hourly)

        Returns:
            Recent weather history data
        """
        params = {
            'location': f'{latitude},{longitude}',
            'units': units,
            'timesteps': timesteps
        }

        logger.info(f"Fetching recent history for location ({latitude}, {longitude})")
        return self._make_request(RECENT_HISTORY_URL, params)

    def get_forecast(
        self,
        latitude: float = LATITUDE,
        longitude: float = LONGITUDE,
        units: str = UNITS,
        timesteps: str = TIMESTEPS
    ) -> Dict[str, Any]:
        """
        Fetch weather forecast for a location.

        Args:
            latitude: Latitude of the location
            longitude: Longitude of the location
            units: Unit system ('metric' or 'imperial')
            timesteps: Time resolution ('1h' for hourly)

        Returns:
            Weather forecast data
        """
        params = {
            'location': f'{latitude},{longitude}',
            'units': units,
            'timesteps': timesteps
        }

        logger.info(f"Fetching forecast for location ({latitude}, {longitude})")
        return self._make_request(FORECAST_URL, params)


def fetch_all_data(latitude: float = LATITUDE, longitude: float = LONGITUDE) -> Dict[str, Dict[str, Any]]:
    """
    Fetch both recent history and forecast data for a location.

    Args:
        latitude: Latitude of the location
        longitude: Longitude of the location

    Returns:
        Dictionary with 'recent_history' and 'forecast' keys containing respective data
    """
    client = TomorrowIOClient()

    logger.info(f"Fetching all data for location ({latitude}, {longitude})")

    try:
        recent_history = client.get_recent_history(latitude, longitude)
        forecast = client.get_forecast(latitude, longitude)

        return {
            'recent_history': recent_history,
            'forecast': forecast
        }
    except RateLimitError as e:
        logger.error(f"Rate limit exceeded for location ({latitude}, {longitude}): {e}")
        raise
    except requests.exceptions.RequestException as e:
        logger.error(f"Failed to fetch data: {e}")
        raise
