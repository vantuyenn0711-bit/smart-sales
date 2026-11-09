FROM python:3.13-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app
RUN pip install --no-cache-dir uv
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev
COPY . .
RUN DJANGO_DEBUG=true DATABASE_URL=postgresql://unused@localhost/unused uv run --no-sync python manage.py collectstatic --noinput \
    && groupadd --system app && useradd --system --gid app app \
    && mkdir -p /app/media && chown -R app:app /app/media /app/staticfiles
USER app
EXPOSE 8000
CMD [".venv/bin/gunicorn", "config.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "2", "--access-logfile", "-", "--error-logfile", "-"]
