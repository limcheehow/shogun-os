# Shogun OS Central Registry
# Multi-stage build keeps the runtime image slim.

FROM python:3.12-slim AS builder

WORKDIR /build
RUN apt-get update && apt-get install -y --no-install-recommends \
        build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt


FROM python:3.12-slim

LABEL org.opencontainers.image.title="shogun-registry" \
      org.opencontainers.image.description="Shogun OS central tenant registry and reverse proxy" \
      org.opencontainers.image.vendor="Shogun OS"

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    ALLOW_INSECURE_LOCAL_DB=false \
    PORT=9000 \
    HOST=0.0.0.0

RUN groupadd --system shogun && useradd --system --gid shogun --home /app shogun \
    && mkdir -p /var/lib/shogun-registry /app \
    && chown -R shogun:shogun /var/lib/shogun-registry /app

WORKDIR /app

COPY --from=builder /install /usr/local
COPY --chown=shogun:shogun \
    main.py \
    api.py \
    models.py \
    database.py \
    router.py \
    config.py \
    cloudflare.py \
    ./

USER shogun

EXPOSE 9000

HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:9000/api/health', timeout=3)"

CMD ["python", "-m", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "9000", "--proxy-headers", "--forwarded-allow-ips", "*"]
