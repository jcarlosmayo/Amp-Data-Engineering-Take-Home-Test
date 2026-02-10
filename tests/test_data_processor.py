"""Tests for tomorrow.data_processor — pure transformation functions."""
from tomorrow.data_processor import flatten_weather_data, process_api_responses


class TestFlattenWeatherData:

    def test_returns_correct_count(self, sample_history_response):
        result = flatten_weather_data(sample_history_response, "recent_history", 25.86, -97.42)
        assert len(result) == 24

    def test_maps_camel_to_snake(self, sample_history_response):
        result = flatten_weather_data(sample_history_response, "recent_history", 25.86, -97.42)
        first = result[0]  # 2023-01-25T10:00:00Z data point

        assert first["temperature"] == 5.13
        assert first["temperature_apparent"] == 5.13
        assert first["dew_point"] == 2.81
        assert first["wind_speed"] == 2.5
        assert first["wind_direction"] == 314.13
        assert first["wind_gust"] == 9.69
        assert first["humidity"] == 85
        assert first["pressure_surface_level"] == 998.13
        assert first["cloud_cover"] == 9
        assert first["weather_code"] == 1000
        assert first["visibility"] == 15.9
        assert first["evapotranspiration"] == 0.035
        assert first["freezing_rain_intensity"] == 0
        assert first["snow_depth"] == 0
        assert first["precipitation_probability"] == 0

    def test_attaches_metadata(self, sample_history_response):
        result = flatten_weather_data(sample_history_response, "recent_history", 25.86, -97.42)
        first = result[0]

        assert first["latitude"] == 25.86
        assert first["longitude"] == -97.42
        assert first["data_type"] == "recent_history"
        assert first["timestamp"] == "2023-01-25T10:00:00Z"

    def test_preserves_raw_data(self, sample_history_response):
        result = flatten_weather_data(sample_history_response, "recent_history", 25.86, -97.42)
        raw = result[0]["raw_data"]

        # raw_data should be the original values dict with camelCase keys
        assert raw == sample_history_response["timelines"]["hourly"][0]["values"]
        assert "temperatureApparent" in raw
        assert "windSpeed" in raw

    def test_empty_response(self):
        assert flatten_weather_data({"timelines": {"hourly": []}}, "forecast", 0, 0) == []
        assert flatten_weather_data({}, "forecast", 0, 0) == []


class TestProcessApiResponses:

    def test_returns_both_types(self, sample_history_response, sample_forecast_response):
        result = process_api_responses(
            recent_history=sample_history_response,
            forecast=sample_forecast_response,
            latitude=25.86,
            longitude=-97.42,
        )

        assert len(result["recent_history"]) == 24
        assert len(result["forecast"]) == 1
        assert all(r["data_type"] == "recent_history" for r in result["recent_history"])
        assert all(r["data_type"] == "forecast" for r in result["forecast"])

        # Verify forecast data comes from the forecast fixture
        forecast_record = result["forecast"][0]
        assert forecast_record["temperature"] == -3.6
        assert forecast_record["wind_speed"] == 6.1
        assert forecast_record["timestamp"] == "2025-02-09T08:00:00Z"
