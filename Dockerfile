# 📡 Sovereign Outpost — Discovery Mesh Dockerfile
# Optimized for Pi Zero 2 W using Debian Slim for Playwright compatibility
# --- Stage 1: Build Dependencies ---
FROM python:3.11-slim as builder
ENV LANG C.UTF-8
ENV LC_ALL C.UTF-8
ENV PYTHONUNBUFFERED=1

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libffi-dev \
    libssl-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /install
COPY requirements.txt /install/
RUN pip install --prefix=/install --no-cache-dir -r requirements.txt

# --- Stage 2: Runtime Image ---
FROM python:3.11-slim
ENV LANG C.UTF-8
ENV LC_ALL C.UTF-8
ENV PYTHONUNBUFFERED=1

WORKDIR /app

# Copy installed packages from builder
COPY --from=builder /install /usr/local

# Install runtime dependencies for Playwright
RUN apt-get update && apt-get install -y --no-install-recommends \
    libnss3 \
    libnspr4 \
    libatk1.0-0 \
    libatk-bridge2.0-0 \
    libcups2 \
    libdrm2 \
    libxkbcommon0 \
    libxcomposite1 \
    libxdamage1 \
    libxfixes3 \
    libxrandr2 \
    libgbm1 \
    libasound2 \
    libpangocairo-1.0-0 \
    libpango-1.0-0 \
    libcairo2 \
    && rm -rf /var/lib/apt/lists/*

# Copy application source
COPY . /app/

# Create persistency directory
RUN mkdir -p /app/harvest

# Metadata
ENV PYTHONPATH=/app
LABEL role="curiosity-outpost"
LABEL standard="MultiSignature2026"

# Default command: Start Heartbeat
CMD ["python", "auditor_cli.py", "heartbeat"]
