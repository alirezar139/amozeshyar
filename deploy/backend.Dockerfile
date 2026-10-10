# Production image for the Django API and the Celery worker (same image, different command).
# Build context: repository root.
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    DJANGO_SETTINGS_MODULE=config.settings.prod

# ffmpeg/ffprobe for video transcoding, libmagic for upload type sniffing.
RUN apt-get update \
    && apt-get install -y --no-install-recommends ffmpeg libmagic1 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY backend/requirements/ requirements/
RUN pip install --no-cache-dir -r requirements/prod.txt

COPY backend/ .
# Static files (Django admin / API docs) are baked in and served by whitenoise.
RUN DJANGO_SECRET_KEY=build-only DJANGO_ALLOWED_HOSTS=localhost CORS_ALLOWED_ORIGINS=http://localhost \
    DATABASE_URL=sqlite:////tmp/build.db python manage.py collectstatic --noinput

RUN useradd --system --uid 1001 app && mkdir -p /app/logs && chown -R app /app
USER app

EXPOSE 8000
# Sync workers + threads; long timeout because lesson videos are uploaded through the API.
CMD ["gunicorn", "config.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "2", "--threads", "2", "--timeout", "600"]
