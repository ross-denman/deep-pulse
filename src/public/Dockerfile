# 📡 Sovereign Outpost — Discovery Mesh Dockerfile
# Lean Alpine Build optimized for Pi Zero 2 W (512MB RAM)

# --- Stage 1: Build Dependencies ---
FROM python:3.11-alpine as builder

RUN apk add --no-cache \
    g++ \
    gcc \
    musl-dev \
    python3-dev \
    libffi-dev \
    openssl-dev \
    make

WORKDIR /install
COPY requirements.txt /install/
RUN pip install --prefix=/install --no-cache-dir -r requirements.txt --break-system-packages

# --- Stage 2: Runtime Image ---
FROM python:3.11-alpine

WORKDIR /app

# Copy installed packages from builder
COPY --from=builder /install /usr/local

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
