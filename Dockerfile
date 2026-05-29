# =============================================================================
# SkyEvents — Multi-stage Dockerfile
#
# Stages:
#   1. python-base   → shared base layer with system deps
#   2. builder       → install Python packages (no dev tools in final image)
#   3. development   → includes dev/test dependencies + hot reload
#   4. production    → minimal, non-root, hardened image
#
# Build args:
#   PYTHON_VERSION   → Python version to use (default: 3.12)
#   APP_ENV          → "development" | "production" (default: production)
# =============================================================================

ARG PYTHON_VERSION=3.12
ARG APP_ENV=production

# -----------------------------------------------------------------------------
# Stage 1: python-base — shared base configuration
# -----------------------------------------------------------------------------
FROM python:${PYTHON_VERSION}-slim-bookworm AS python-base

# Prevent .pyc files and ensure stdout/stderr are unbuffered
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONFAULTHANDLER=1 \
    # pip
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_DEFAULT_TIMEOUT=100 \
    # Application
    APP_HOME=/app

WORKDIR ${APP_HOME}

# Install system dependencies required by psycopg and Pillow
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        # psycopg (PostgreSQL)
        libpq-dev \
        # Pillow
        libjpeg-dev \
        libpng-dev \
        libwebp-dev \
        # General utilities
        curl \
        tini \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# -----------------------------------------------------------------------------
# Stage 2: builder — install Python dependencies
# -----------------------------------------------------------------------------
FROM python-base AS builder

ARG APP_ENV

# Install build tools (only needed during build, not in final image)
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        gcc \
        g++ \
        build-essential \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY requirements/ requirements/

# Install dependencies into a virtual environment for clean separation
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

RUN pip install --upgrade pip wheel setuptools

# Install the correct requirements set based on APP_ENV
RUN if [ "${APP_ENV}" = "development" ]; then \
        pip install -r requirements/dev.txt; \
    elif [ "${APP_ENV}" = "test" ]; then \
        pip install -r requirements/test.txt; \
    else \
        pip install -r requirements/production.txt; \
    fi

# -----------------------------------------------------------------------------
# Stage 3: development
# -----------------------------------------------------------------------------
FROM python-base AS development

ENV APP_ENV=development \
    DJANGO_SETTINGS_MODULE=config.settings.local \
    PATH="/opt/venv/bin:$PATH"

COPY --from=builder /opt/venv /opt/venv

# Copy the entire project
COPY . .

# Create a non-root user for development too
RUN groupadd --gid 1001 skyevents \
    && useradd --uid 1001 --gid skyevents --no-create-home skyevents \
    && chown -R skyevents:skyevents /app

USER skyevents

EXPOSE 8000

ENTRYPOINT ["/usr/bin/tini", "--"]
CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]

# -----------------------------------------------------------------------------
# Stage 4: production
# -----------------------------------------------------------------------------
FROM python-base AS production

ENV APP_ENV=production \
    DJANGO_SETTINGS_MODULE=config.settings.production \
    PATH="/opt/venv/bin:$PATH" \
    # Security: disable debug output in production
    PYTHONDEBUG=0

COPY --from=builder /opt/venv /opt/venv

# Copy only necessary application files (no tests, no docs)
COPY manage.py .
COPY config/ config/
COPY sky_events/ sky_events/

# Create non-root user — NEVER run production containers as root
RUN groupadd --gid 1001 skyevents \
    && useradd --uid 1001 --gid skyevents --shell /bin/false --no-create-home skyevents \
    # Create directories with correct ownership
    && mkdir -p /app/staticfiles /app/media \
    && chown -R skyevents:skyevents /app

USER skyevents

# Collect static files at build time
RUN python manage.py collectstatic --noinput --clear 2>/dev/null || true

EXPOSE 8000

# Health check — uses the /health/ endpoint
HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
    CMD curl -f http://localhost:8000/health/ || exit 1

# Use tini as init process to handle signals correctly
ENTRYPOINT ["/usr/bin/tini", "--"]
CMD ["gunicorn", "config.wsgi:application", \
     "--bind", "0.0.0.0:8000", \
     "--workers", "4", \
     "--worker-class", "sync", \
     "--worker-tmp-dir", "/dev/shm", \
     "--timeout", "30", \
     "--graceful-timeout", "30", \
     "--max-requests", "1000", \
     "--max-requests-jitter", "50", \
     "--access-logfile", "-", \
     "--error-logfile", "-", \
     "--log-level", "info"]
