# ===== Stage 1: Build frontend =====
FROM node:20-alpine AS frontend-build
WORKDIR /app/frontend
COPY frontend/package*.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

# ===== Stage 2: Production =====
FROM python:3.12-slim

# Install nginx and supervisor
RUN apt-get update && \
    apt-get install -y --no-install-recommends nginx supervisor && \
    rm -rf /var/lib/apt/lists/*

# Setup backend
WORKDIR /app/backend
COPY backend/requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY backend/ ./

# Copy frontend build to nginx directory
COPY --from=frontend-build /app/frontend/dist /var/www/lifequest

# Copy nginx config
COPY deploy/nginx.conf /etc/nginx/sites-available/lifequest
RUN ln -sf /etc/nginx/sites-available/lifequest /etc/nginx/sites-enabled/lifequest && \
    rm -f /etc/nginx/sites-enabled/default

# Copy supervisor config
COPY deploy/supervisord.conf /etc/supervisor/conf.d/lifequest.conf

# Create data directories (will be mounted as volumes)
RUN mkdir -p /app/data/uploads/avatars \
             /app/data/uploads/notes \
             /app/data/notes_data

# Symlink data dirs so the app finds them where it expects
RUN ln -sf /app/data/uploads /app/backend/uploads && \
    ln -sf /app/data/notes_data /app/backend/notes_data && \
    ln -sf /app/data/lifequest.db /app/backend/lifequest.db 2>/dev/null; true

# Entrypoint script
COPY deploy/entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

EXPOSE 80

VOLUME ["/app/data"]

ENTRYPOINT ["/entrypoint.sh"]
