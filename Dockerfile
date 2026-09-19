# A Dockerfile, not a Render-specific build config.
#
# DEPLOYMENT section 10: the test of portability is whether moving host means
# editing application code. With a Dockerfile, moving from Render to Fly.io or
# to any VPS is a change of deploy target and a connection string - nothing else.

FROM python:3.13-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# Dependencies first, so a code change does not reinstall every package.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Render and most hosts hand the port in through $PORT.
ENV PORT=8000
EXPOSE 8000

CMD ["sh", "-c", "uvicorn api.main:app --host 0.0.0.0 --port ${PORT}"]
