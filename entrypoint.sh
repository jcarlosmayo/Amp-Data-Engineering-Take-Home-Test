#!/bin/bash
set -e

echo "=================================================="
echo "TOMORROW.IO WEATHER SCRAPER - CRON SERVICE"
echo "=================================================="
echo "Starting cron-based hourly weather data scraping"
echo ""

# Create log file for cron output
touch /var/log/cron.log
chmod 0666 /var/log/cron.log

echo "✓ Log file created at /var/log/cron.log"

# Generate crontab with environment variables from container
# Cron runs with minimal environment, so we must explicitly set variables
cat > /tmp/crontab.tmp << EOF
# Environment variables for cron jobs (injected from container environment)
SHELL=/bin/bash
PATH=/usr/local/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin
API_KEY=${API_KEY}
PGHOST=${PGHOST}
PGPORT=${PGPORT}
PGDATABASE=${PGDATABASE}
PGUSER=${PGUSER}
PGPASSWORD=${PGPASSWORD}

# Run weather scraper every hour at the start of the hour
0 * * * * cd /app && /usr/local/bin/python -m tomorrow >> /var/log/cron.log 2>&1

EOF

# Install the generated crontab
crontab /tmp/crontab.tmp
echo "✓ Crontab installed with environment variables (runs every hour at :00)"

# Show the installed crontab
echo ""
echo "Installed cron schedule:"
crontab -l
echo ""

# Start cron daemon in background
echo "✓ Starting cron daemon..."
/usr/sbin/cron &

# Run the script immediately on startup (don't wait for first hour)
echo ""
echo "=================================================="
echo "RUNNING INITIAL SCRAPE (immediate execution)"
echo "=================================================="
cd /app && python -m tomorrow
echo ""
echo "✓ Initial scrape completed"
echo ""

echo "=================================================="
echo "CRON SERVICE RUNNING"
echo "=================================================="
echo "Script will now run every hour at :00 minutes"
echo "Logs are being written to /var/log/cron.log"
echo "Container will remain running..."
echo "=================================================="
echo ""

# Tail the log file to keep container running and show output
exec tail -f /var/log/cron.log
