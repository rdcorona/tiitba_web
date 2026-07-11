# Stage 1: Build frontend
FROM node:20-alpine AS frontend-build
WORKDIR /app
COPY frontend/package.json frontend/package-lock.json* ./
RUN npm install
COPY frontend/ ./
RUN npm run build

# Stage 2: Python backend + built frontend
# Usamos la imagen completa en lugar de -slim para evitar problemas de apt-get
FROM python:3.11
WORKDIR /app

# Intentamos omitir el apt-get update si la red falla. 
# La imagen python:3.11 estándar ya incluye la mayoría de librerías base.
# Solo instalamos lo mínimo necesario si es que falta.
RUN apt-get update || true && apt-get install -y \
    libgl1-mesa-glx \
    libglib2.0-0 \
    || echo "Warning: Could not install system libs, proceeding anyway..."

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY backend/ backend/
COPY --from=frontend-build /app/dist /app/frontend/dist

# Create storage directory for session persistence
RUN mkdir -p /app/storage

EXPOSE 8000

ENV TIITBA_STORAGE_DIR=/app/storage

CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000"]
