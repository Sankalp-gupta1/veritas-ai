FROM node:24-bookworm-slim AS frontend
WORKDIR /build/frontend
COPY frontend/package*.json ./
RUN npm ci --no-audit --no-fund
COPY frontend/ ./
RUN npm run build

FROM python:3.12-slim-bookworm AS runtime
WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 MODEL_DIR=/app/models
COPY requirements.lock.txt ./
RUN pip install --no-cache-dir -r requirements.lock.txt
COPY scripts/download_models.py scripts/download_models.py
RUN python scripts/download_models.py
COPY app/ app/
COPY migrations/ migrations/
COPY scripts/migrate.py scripts/migrate.py
COPY samples/ samples/
COPY research/results/ research/results/
COPY --from=frontend /build/frontend/dist frontend/dist
RUN useradd --create-home --uid 10001 veritas
USER veritas
EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]

