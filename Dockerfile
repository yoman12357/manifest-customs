FROM node:24-alpine AS ui
WORKDIR /build/frontend
COPY frontend/package*.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build
FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt
COPY backend/ backend/
COPY scripts/ scripts/
COPY --from=ui /build/frontend/dist frontend/dist
RUN useradd --create-home manifest && mkdir -p /app/data /app/samples && chown -R manifest:manifest /app
USER manifest
ENV DATA_DIR=/app/data
EXPOSE 8000
CMD ["sh","-c","python -m scripts.seed && uvicorn backend.main:app --host 0.0.0.0 --port ${PORT:-8000} --workers 1"]
