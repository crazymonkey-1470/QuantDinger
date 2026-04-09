# QuantDinger Backend API Dockerfile
# BASE_IMAGE can be overridden from docker-compose/.env.
ARG BASE_IMAGE=python:3.12-slim-bookworm
FROM ${BASE_IMAGE}

# Set working directory
WORKDIR /app

# Use HTTPS mirror and install minimal runtime dependencies.
# Keep image lean to avoid long downloads of full compiler toolchains.
RUN sed -i 's|http://deb.debian.org|https://deb.debian.org|g' /etc/apt/sources.list.d/*.sources 2>/dev/null || true \
    && apt-get update \
    && apt-get install -y --no-install-recommends --fix-missing \
    ca-certificates \
    curl \
    # Build deps (needed for some pyproject-based packages like ed25519-blake2b)
    build-essential \
    python3-dev \
    libffi-dev \
    libssl-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy dependency file
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir --prefer-binary --timeout 120 -r requirements.txt \
    # Remove build deps to keep image small
    && apt-get purge -y --auto-remove build-essential python3-dev libffi-dev libssl-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy application code
COPY . .

# Copy and set up entrypoint script
COPY docker-entrypoint.sh /usr/local/bin/
RUN sed -i 's/\r$//' /usr/local/bin/docker-entrypoint.sh \
    && chmod +x /usr/local/bin/docker-entrypoint.sh

# Create log and data directories
RUN mkdir -p logs data/memory

# Expose port
EXPOSE 5000

# Environment variables
ENV PYTHONUNBUFFERED=1
ENV PYTHON_API_HOST=0.0.0.0
ENV PYTHON_API_PORT=5000

# Use entrypoint script to check SECRET_KEY before starting
ENTRYPOINT ["/usr/local/bin/docker-entrypoint.sh"]

# Start command (gunicorn for production; override with CMD ["python", "run.py"] for dev)
CMD ["gunicorn", "-c", "gunicorn_config.py", "run:app"]
