"""Tests for tomorrow.db_client — upsert behavior with mocked psycopg2."""
import json
from unittest.mock import MagicMock, patch

import pytest

from tomorrow.db_client import DatabaseClient


@pytest.fixture
def mock_db():
    """Provide a DatabaseClient with a mocked psycopg2 connection."""
    with patch("tomorrow.db_client.psycopg2.connect") as mock_connect:
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value.__enter__ = MagicMock(return_value=mock_cursor)
        mock_conn.cursor.return_value.__exit__ = MagicMock(return_value=False)
        mock_connect.return_value = mock_conn

        client = DatabaseClient(connection_string="host=mock")
        client.connect()

        yield client, mock_cursor


class TestInsertWeatherData:

    def test_calls_execute_batch(self, mock_db, sample_flat_record):
        client, mock_cursor = mock_db

        with patch("tomorrow.db_client.execute_batch") as mock_exec:
            client.insert_weather_data([sample_flat_record])

            mock_exec.assert_called_once()
            args = mock_exec.call_args
            assert args[0][0] is mock_cursor  # cursor
            assert len(args[0][2]) == 1  # one record

    def test_upsert_sql_contains_conflict_clause(self, mock_db, sample_flat_record):
        client, _ = mock_db

        with patch("tomorrow.db_client.execute_batch") as mock_exec:
            client.insert_weather_data([sample_flat_record])

            sql = mock_exec.call_args[0][1]
            assert "INSERT INTO weather_data" in sql
            assert "ON CONFLICT (latitude, longitude, timestamp, data_type)" in sql
            assert "DO UPDATE SET" in sql
            assert "temperature = EXCLUDED.temperature" in sql

    def test_serializes_raw_data_to_json(self, mock_db, sample_flat_record):
        client, _ = mock_db
        original_raw = sample_flat_record["raw_data"].copy()

        with patch("tomorrow.db_client.execute_batch"):
            client.insert_weather_data([sample_flat_record])

        # raw_data should have been converted from dict to JSON string in-place
        assert isinstance(sample_flat_record["raw_data"], str)
        assert json.loads(sample_flat_record["raw_data"]) == original_raw
