# MES AI Server — Docker image
#
# Build context: server/
# Build: docker build -t mes-ai-server .   (from server/)
# Or via root compose: docker compose build mes-server

FROM python:3.12-slim

# Install OS-level build deps required by asyncpg (C extension)
RUN apt-get update \
    && apt-get install -y --no-install-recommends gcc libpq-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy project metadata first so pip layer is cached when only source changes
COPY pyproject.toml .

# Install the mes package and its core dependencies
RUN pip install --no-cache-dir -e .

# Copy application source
COPY src/     src/
COPY alembic/ alembic/
COPY alembic.ini .
COPY scripts/ scripts/
COPY plugins/ plugins/

# Create the log directory the server writes to
RUN mkdir -p logs

# Copy and register the entrypoint
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

EXPOSE 8082

ENTRYPOINT ["/entrypoint.sh"]
