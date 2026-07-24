# Backend API and worker share this image (different command in compose).
# Build from repository root: docker build -t edgar-backend .

FROM python:3.12-slim-bookworm

WORKDIR /app

ENV PYTHONPATH=/app \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# Install deps before copying source for better layer caching.
COPY requirements.txt requirements-backend.txt ./
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt -r requirements-backend.txt

COPY backend ./backend
COPY edgar_project ./edgar_project
COPY agentic ./agentic
COPY src ./src
COPY config.py ./
COPY alembic ./alembic
COPY alembic.ini ./
COPY tests/__init__.py ./tests/__init__.py
COPY tests/support ./tests/support
COPY docker-entrypoint.sh /docker-entrypoint.sh
RUN chmod +x /docker-entrypoint.sh \
    && useradd --create-home --shell /bin/bash --uid 1000 appuser \
    && chown -R appuser:appuser /app

# Drop privileges after fixing artifact volume permissions (see entrypoint).
USER root
ENTRYPOINT ["/docker-entrypoint.sh"]
EXPOSE 8000
CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000"]
