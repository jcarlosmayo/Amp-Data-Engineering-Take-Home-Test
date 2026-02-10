# Amperon Weather Data Pipeline

## Project Overview

This project implements a weather data scraping system that fetches hourly forecasts and historical observations from the Tomorrow.io API for 10 geographic locations in South Texas (near Brownsville). The data is stored in PostgreSQL and analyzed using Jupyter notebooks.

**Assignment Requirements:**
- Query latest temperature and wind speed for all 10 locations
- Display hourly time series from 1 day ago to 5 days in the future
- Scrape data hourly for continuous monitoring

---

## Quick Start Guide

### Prerequisites

- **Docker** and **Docker Compose** installed
- **Tomorrow.io API Key** (set as environment variable)
- **Ports available**: 5432 (PostgreSQL), 8888 (Jupyter)

### Environment Setup

1. **Set your API key** (required):
   ```bash
   export API_KEY="your_tomorrow_io_api_key_here"
   ```

   Or create a `.env` file in the project root:
   ```bash
   echo "API_KEY=your_tomorrow_io_api_key_here" > .env
   ```

### Starting the System

2. **Build and start all services**:
   ```bash
   docker compose up --build
   ```

   This will start three services:
   - `postgres` - PostgreSQL database (port 5432)
   - `tomorrow` - Weather scraper with cron (runs hourly)
   - `jupyter` - Jupyter notebook server (port 8888)

3. **What happens on startup**:
   - Database schema is created automatically
   - Weather scraper runs **immediately** for all 10 locations (~1,440 records)
   - Cron schedules hourly scraping (at :00 minutes every hour)
   - Jupyter notebook becomes available at http://localhost:8888

### Accessing Services

**Jupyter Notebook** (data analysis):
```
http://localhost:8888
```
- No password required
- Open `analysis.ipynb` to see queries and visualizations

**PostgreSQL Database** (direct access):
```bash
PGHOST=localhost PGPORT=5432 PGDATABASE=tomorrow PGUSER=postgres PGPASSWORD=postgres psql
```

**View Scraper Logs** (real-time):
```bash
docker compose logs -f tomorrow
```

### Verification

**Check if data is being scraped**:
```bash
# Connect to database
PGHOST=localhost PGPORT=5432 PGDATABASE=tomorrow PGUSER=postgres PGPASSWORD=postgres psql

# Query record count
SELECT COUNT(*) FROM weather_data;
-- Expected: ~1,440 records after first run

# Query latest data by location
SELECT latitude, longitude, temperature, wind_speed, timestamp
FROM weather_data
WHERE data_type = 'recent_history'
ORDER BY timestamp DESC
LIMIT 10;
```

**Check cron schedule**:
```bash
docker compose exec tomorrow crontab -l
```

**View cron logs**:
```bash
docker compose exec tomorrow tail -f /var/log/cron.log
```

### Stopping the System

**Stop services** (keeps data):
```bash
docker compose down
```

**Stop and remove all data**:
```bash
docker compose down --volumes
```

### Troubleshooting

**API Key not set**:
```
Error: API_KEY environment variable not found
```
Solution: Set `export API_KEY="your_key"` before running `docker compose up`

**Port already in use**:
```
Error: bind: address already in use
```
Solution: Stop other services using ports 5432 or 8888

**No data in database**:
- Check logs: `docker compose logs tomorrow`
- Verify API key is valid
- Check network connectivity to Tomorrow.io API

**Rate limit exceeded (429 error)**:
```
WARNING - ⚠️  Rate limit exceeded (429). API requests: 25/hour limit reached.
```
- System automatically retries with exponential backoff (60s, 120s, 240s)
- Check logs: `docker compose logs tomorrow` to monitor retry attempts
- Tomorrow.io free tier: 25 API calls per hour
- Current usage: 20 calls/hour (10 locations × 2 endpoints)
- Avoid manual script runs during cron execution times

---

## Database Design Decisions

### Single Table with Discriminator vs Multiple Tables

**Chosen Approach: Single Table with `data_type` Discriminator Column**

```sql
CREATE TABLE weather_data (
    id SERIAL PRIMARY KEY,
    latitude DECIMAL(10, 6) NOT NULL,
    longitude DECIMAL(10, 6) NOT NULL,
    timestamp TIMESTAMP WITH TIME ZONE NOT NULL,
    data_type VARCHAR(50) NOT NULL,  -- 'recent_history' or 'forecast'
    temperature DECIMAL(5, 2),
    wind_speed DECIMAL(5, 2),
    -- ... other weather fields
    UNIQUE(latitude, longitude, timestamp, data_type)
);
```

**Why Single Table?**

1. **Simplified Time Series Queries** — The assignment requires querying data "from 1 day ago to 5 days in the future" — a continuous timeline spanning both history and forecast. With a single table, this is trivial:

```sql
SELECT timestamp, temperature, data_type
FROM weather_data
WHERE latitude = 25.86 AND longitude = -97.42
  AND timestamp BETWEEN NOW() - INTERVAL '1 day' AND NOW() + INTERVAL '5 days'
ORDER BY timestamp;
```

With separate tables, this requires complex joins or unions across multiple tables.

2. **No Schema Duplication** — Both historical observations and forecasts contain identical weather variables (temperature, wind speed, humidity, etc.). Separate tables would duplicate this schema definition, violating the DRY principle.

3. **Unified Maintenance** — Single set of indexes to manage, one table to backup/restore, simpler migrations when adding new weather variables.

4. **Forecast Accuracy Analysis** — As time passes, forecasts become "past forecasts" that can be compared against actual observations:

```sql
SELECT
    timestamp,
    MAX(CASE WHEN data_type = 'forecast' THEN temperature END) as forecasted_temp,
    MAX(CASE WHEN data_type = 'recent_history' THEN temperature END) as actual_temp
FROM weather_data
GROUP BY timestamp;
```

5. **Industry Standards** — Time-series databases (InfluxDB, TimescaleDB) use tags/labels to distinguish data types within a single measurement, mirroring this discriminator pattern.

**Alternative considered (separate tables):** Rejected because it requires UNION for continuous timelines, duplicates schema, and complicates application logic. Separate tables would be better if history and forecast had different schemas or different retention policies.

| Criteria | Single Table (Chosen) | Separate Tables |
|----------|----------------------|-----------------|
| Query Simplicity | Simple | Complex (UNION) |
| Schema Maintenance | One table | Two tables |
| Time Series Queries | Native | Requires UNION |
| Forecast Accuracy | Easy | Complex |

---

### Wide Format vs Long Format (EAV)

**Chosen Approach: Wide Format (Columnar Schema)**

Each weather variable is a separate column:

```sql
CREATE TABLE weather_data (
    -- identifiers
    latitude, longitude, timestamp, data_type,

    -- temperature fields
    temperature DECIMAL(5, 2),
    temperature_apparent DECIMAL(5, 2),
    dew_point DECIMAL(5, 2),

    -- wind fields
    wind_speed DECIMAL(5, 2),
    wind_direction DECIMAL(5, 2),
    wind_gust DECIMAL(5, 2),

    -- 30+ other weather variables...
);
```

**Why Wide Format?**

1. **Query Simplicity** — The assignment asks for "latest temperature and wind speed for each location":

```sql
-- Wide format: Simple and readable
SELECT latitude, longitude, temperature, wind_speed
FROM weather_data
WHERE data_type = 'recent_history'
ORDER BY timestamp DESC;
```

With long format, this would require self-joins or pivoting:

```sql
-- Long format: Complex self-joins
SELECT
    t.latitude, t.longitude,
    temp.value as temperature,
    wind.value as wind_speed
FROM weather_observations t
LEFT JOIN weather_observations temp
    ON t.id = temp.observation_id AND temp.variable_name = 'temperature'
LEFT JOIN weather_observations wind
    ON t.id = wind.observation_id AND wind.variable_name = 'wind_speed';
```

2. **Performance** — 1,440 rows (wide) vs 43,200+ rows (long format with ~30 variables). Single row scan gets all variables vs multiple joins.

3. **Type Safety** — Strong typing per variable (`DECIMAL(5, 2)`) vs generic column with type ambiguity.

4. **Analytics-Friendly** — Jupyter notebooks and pandas work naturally with wide format:

```python
# Wide format: Direct query to DataFrame
df = pd.read_sql("SELECT * FROM weather_data", engine)
df.plot(x='timestamp', y=['temperature', 'wind_speed'])

# Long format: Requires pivoting first
df = pd.read_sql("SELECT * FROM weather_observations", engine)
df_pivoted = df.pivot(index='timestamp', columns='variable_name', values='variable_value')
```

5. **Known Schema** — Tomorrow.io API returns a fixed set of ~30 weather variables. The schema is stable, so the flexibility advantage of long format provides no benefit.

**Alternative considered (EAV/long format):** Rejected because it requires self-joins for multi-variable queries, loses type safety, produces 30x more rows, and requires pivoting for analysis. Long format would be better for highly dynamic schemas or sparse data.

| Criteria | Wide Format (Chosen) | Long Format (EAV) |
|----------|---------------------|-------------------|
| Query Simplicity | Simple SELECT | Self-joins |
| Performance | 1,440 rows | 43,200+ rows |
| Type Safety | Strong typing | Generic column |
| Analytics | Direct use | Requires pivot |
| Schema Flexibility | ALTER TABLE | No changes needed |

---

### Hybrid Approach: Wide Format + JSONB

On top of the wide format, each row stores the complete API response as JSONB:

```sql
CREATE TABLE weather_data (
    -- Structured columns for fast queries
    temperature DECIMAL(5, 2),
    wind_speed DECIMAL(5, 2),
    -- ... 30+ weather columns

    -- Raw JSON for flexibility
    raw_data JSONB  -- Complete API response: {"temperature": 11.64, "windSpeed": 1.0, ...}
);
```

This provides fast structured queries on typed columns, flexibility to query new/uncommon fields via JSONB, future-proofing if Tomorrow.io adds new variables, and debugging capability via the original API response.

```sql
-- Query a field not in structured columns
SELECT
    timestamp,
    temperature,  -- from typed column (fast)
    raw_data->>'uvIndex' as uv_index  -- from JSONB (flexible)
FROM weather_data;
```

---

### Direct Loading vs File Staging

**Chosen Approach: Direct API → Database Pipeline**

The current pipeline ([tomorrow/pipeline.py](tomorrow/pipeline.py)) fetches, transforms, and loads data in a single pass without staging raw API responses to disk.

**Alternative considered (two-stage):** Save raw JSON to disk first (`API → JSON files → database`), then load from files. This would decouple extraction from loading, meaning a database failure would never waste rate-limited API calls — you'd just replay from the files. It also enables reprocessing from raw data if the schema or transformation logic changes.

**Why we chose direct loading:**
- The `raw_data` JSONB column already preserves the complete API response inside the database, covering the reprocessability need.
- The upsert logic (`ON CONFLICT ... DO UPDATE`) makes the pipeline idempotent, so re-running after a failure is safe.
- With only 10 locations and small payloads, file management overhead (naming, cleanup, tracking loaded files) adds complexity without proportional benefit.

**When file staging would be better:**
- High API costs or strict rate limits where re-fetching is unacceptable
- Large payloads where database inserts are slow or failure-prone
- Need to reprocess data with different transformation logic without re-fetching

---

### Data Integrity and Idempotency

**UNIQUE Constraint:**

```sql
UNIQUE(latitude, longitude, timestamp, data_type)
```

Prevents duplicate records for the same location, time, and data type while allowing intentional overlap between forecast and history for the same timestamp (one is a prediction, the other is an actual observation).

**ON CONFLICT Upsert Logic:**

```sql
INSERT INTO weather_data (...)
VALUES (...)
ON CONFLICT (latitude, longitude, timestamp, data_type)
DO UPDATE SET
    temperature = EXCLUDED.temperature,
    wind_speed = EXCLUDED.wind_speed,
    -- ... update all weather fields
    created_at = CURRENT_TIMESTAMP;
```

Safe to run the scraper multiple times — no duplicate errors, updates existing records if API data changes, and provides idempotent behavior for hourly cron jobs.

**Implementation:** [tomorrow/db_client.py:188-222](tomorrow/db_client.py#L188-L222)

### Location Configuration

The system scrapes 10 specific locations in South Texas, defined as Python constants in [tomorrow/config.py](tomorrow/config.py):

```python
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
```

Python constants over environment variables because locations are fixed per assignment (not runtime config), are simple and type-safe, and keep all configuration in one place.

### Data Distribution

- **Total records**: 1,440
- **Forecast records**: 1,200
- **Historical records**: 240
- **Records per location**: ~144 (120 forecast + 24 history)
- **Temporal coverage**: 2026-02-06 to 2026-02-13 (7 days)

---

## Schema Overview

```sql
CREATE TABLE weather_data (
    -- Primary key
    id SERIAL PRIMARY KEY,

    -- Location and time identifiers
    latitude DECIMAL(10, 6) NOT NULL,
    longitude DECIMAL(10, 6) NOT NULL,
    timestamp TIMESTAMP WITH TIME ZONE NOT NULL,
    data_type VARCHAR(50) NOT NULL,  -- 'recent_history' or 'forecast'

    -- Temperature fields
    temperature DECIMAL(5, 2),
    temperature_apparent DECIMAL(5, 2),
    dew_point DECIMAL(5, 2),

    -- Wind fields
    wind_speed DECIMAL(5, 2),
    wind_direction DECIMAL(5, 2),
    wind_gust DECIMAL(5, 2),

    -- Atmospheric fields
    humidity DECIMAL(5, 2),
    pressure_surface_level DECIMAL(7, 2),
    pressure_sea_level DECIMAL(7, 2),

    -- Cloud fields
    cloud_cover DECIMAL(5, 2),
    cloud_base DECIMAL(7, 2),
    cloud_ceiling DECIMAL(7, 2),

    -- Precipitation - rain
    rain_intensity DECIMAL(5, 2),
    rain_accumulation DECIMAL(5, 2),

    -- Precipitation - snow
    snow_intensity DECIMAL(5, 2),
    snow_accumulation DECIMAL(5, 2),
    snow_depth DECIMAL(5, 2),

    -- Precipitation - other
    sleet_intensity DECIMAL(5, 2),
    freezing_rain_intensity DECIMAL(5, 2),
    ice_accumulation DECIMAL(5, 2),
    precipitation_probability DECIMAL(5, 2),

    -- UV and visibility
    uv_index INTEGER,
    visibility DECIMAL(7, 2),

    -- Other
    weather_code INTEGER,

    -- Raw data for flexibility
    raw_data JSONB,

    -- Metadata
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,

    -- Constraints
    UNIQUE(latitude, longitude, timestamp, data_type)
);
```

**Indexing Strategy:**

```sql
-- Primary key for row identification
id SERIAL PRIMARY KEY

-- Unique constraint doubles as index
UNIQUE(latitude, longitude, timestamp, data_type)

-- Additional indexes for common queries (consider adding):
CREATE INDEX idx_timestamp ON weather_data(timestamp);
CREATE INDEX idx_location ON weather_data(latitude, longitude);
CREATE INDEX idx_data_type ON weather_data(data_type);
```

---

## Architecture and Resilience

### Error and Exception Handling

The pipeline is designed to be resilient — individual failures don't crash the service, and the hourly cron schedule provides automatic recovery.

Each of the 10 locations is processed independently in [tomorrow/__main__.py](tomorrow/__main__.py). If one location fails (due to rate limits, network errors, or API issues), the remaining locations still get processed:

```
✓ Location (25.86, -97.42) completed: 188 records
⏳ Location (25.90, -97.52) skipped due to rate limit
✗ Location (25.90, -97.48) failed: Connection timeout
✓ Location (25.90, -97.44) completed: 188 records
...
⚠ 2/10 locations failed (will retry next hour)
```

The service always exits with code 0 so the container stays alive for the next cron run. Failed locations are automatically retried on the next hourly cron run.

| Layer | File | Handles | Behavior |
|-------|------|---------|----------|
| HTTP request | [api_client.py](tomorrow/api_client.py) `_make_request` | 429 rate limit | Raises `RateLimitError`, retried by tenacity (3 attempts, exponential backoff 60-300s) |
| HTTP request | [api_client.py](tomorrow/api_client.py) `_make_request` | Timeout, connection errors, other HTTP errors | Logged and re-raised |
| Data fetching | [api_client.py](tomorrow/api_client.py) `fetch_all_data` | `RateLimitError`, `RequestException` | Logged with location context and re-raised |
| Pipeline | [pipeline.py](tomorrow/pipeline.py) `run_pipeline` | All exceptions | Logged with traceback and re-raised |
| Main loop | [__main__.py](tomorrow/__main__.py) `main` | `RateLimitError` | Logs warning, skips location, continues loop |
| Main loop | [__main__.py](tomorrow/__main__.py) `main` | All other exceptions | Logs error, skips location, continues loop |

### API Rate Limit Handling

**Tomorrow.io API Limits:**
- Free tier: **25 calls per hour**
- Current usage: **20 calls per hour** (10 locations × 2 endpoints)
- Headroom: **5 calls** (20% buffer)

When rate limit is exceeded (HTTP 429), the system automatically:

1. Detects 429 status code from API
2. Logs warning with retry timing
3. Retries with exponential backoff (60s, 120s, 240s)
4. Maximum 3 retries before failing
5. Respects `Retry-After` header if provided

**Implementation** ([tomorrow/api_client.py](tomorrow/api_client.py)):

```python
@retry(
    retry=retry_if_exception_type(RateLimitError),
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=60, max=300)
)
def _make_request(self, url: str, params: Dict[str, Any]) -> Dict[str, Any]:
    # Detects 429 and raises RateLimitError
    # Automatic retry with exponential backoff
```

**Monitoring:**

```bash
# View last 50 log lines for rate limit messages
docker compose exec tomorrow tail -50 /var/log/cron.log | grep -i "rate\|429"

# Check how many times scraper ran in last hour
docker compose exec tomorrow grep "PIPELINE COMPLETED" /var/log/cron.log | tail -5
```

### Security Review

A security review was conducted covering all application code, Docker configuration, and shell scripts. **No high-confidence vulnerabilities were found.**

| Area | Finding | Verdict |
|------|---------|---------|
| SQL queries ([db_client.py](tomorrow/db_client.py)) | INTERVAL clause uses `%s` placeholders | Safe — psycopg2 parameterized queries handle these correctly |
| API key logging ([api_client.py](tomorrow/api_client.py)) | `logger.debug()` includes params with API key | Safe — DEBUG logging is disabled by default (level=INFO) |
| API key in config ([config.py](tomorrow/config.py)) | Hardcoded fallback key in `os.getenv()` | Acceptable — free-tier test key, overridden by environment variable |
| Crontab credentials ([entrypoint.sh](entrypoint.sh)) | Environment variables written to `/tmp/crontab.tmp` | Acceptable — single-purpose Docker container with no privilege boundaries |
| Jupyter authentication ([docker-compose.yaml](docker-compose.yaml)) | Token and password disabled | Acceptable — intentional local development configuration, localhost only |

All database queries use parameterized queries via psycopg2. Upsert logic uses `ON CONFLICT ... DO UPDATE` to prevent duplicate injection. No user-facing HTTP endpoints exist (scraper runs on cron, no web server).

---

## Key Files

- **Schema Definition**: [tomorrow/db_client.py](tomorrow/db_client.py) (lines 52-133)
- **Data Insertion**: [tomorrow/db_client.py](tomorrow/db_client.py) (lines 156-223)
- **Pipeline Logic**: [tomorrow/pipeline.py](tomorrow/pipeline.py)
- **Configuration**: [tomorrow/config.py](tomorrow/config.py)
- **Analysis**: [analysis.ipynb](analysis.ipynb)
- **Assignment Requirements**: [ASSIGNMENT.md](ASSIGNMENT.md)
