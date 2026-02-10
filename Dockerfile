FROM python:3.11.7@sha256:63bec515ae23ef6b4563d29e547e81c15d80bf41eff5969cb43d034d333b63b8

WORKDIR /app
ENV PATH="/app/.venv/bin:$PATH"
ENV PIP_DISABLE_PIP_VERSION_CHECK=1
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

# Install cron
RUN apt-get update && apt-get install -y cron && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY ./requirements.txt .
RUN python -m pip install -r requirements.txt

# Copy application code
COPY ./tomorrow /app/tomorrow

# Copy cron configuration and entrypoint script
COPY ./crontab /app/crontab
COPY ./entrypoint.sh /app/entrypoint.sh
RUN chmod +x /app/entrypoint.sh

# Note: cron daemon requires root, so no USER switch here.
# Set entrypoint for cron-based execution
CMD ["/app/entrypoint.sh"]
