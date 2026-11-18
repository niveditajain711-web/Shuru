FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app ./app

# The SQLite run store lives in /app/data, which compose mounts as a volume.
# Secrets are NOT copied into the image: they arrive as environment variables at run time.
RUN useradd --create-home --uid 1000 app && mkdir -p /app/data && chown -R app:app /app/data
USER app

EXPOSE 8000
# --proxy-headers lets the rate limiter see the real client IP forwarded by Caddy. This is safe because
# port 8000 is only reachable from inside the compose network, never published to the internet.
CMD ["uvicorn", "app.main:create_default_app", "--factory", "--host", "0.0.0.0", "--port", "8000", "--proxy-headers", "--forwarded-allow-ips=*"]
