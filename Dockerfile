### --- FRONTEND BUILD STAGE --- ###
FROM node:25-bookworm-slim AS frontend-build
WORKDIR /app/web

# Build-time environment variables for React
ARG REACT_APP_AZURE_CLIENT_ID
ARG REACT_APP_AZURE_TENANT_ID
ARG REACT_APP_AZURE_SCOPE
ARG REACT_APP_API_DEV_BASE_URL
ARG NODE_ENV=production

ENV REACT_APP_AZURE_CLIENT_ID=$REACT_APP_AZURE_CLIENT_ID
ENV REACT_APP_AZURE_TENANT_ID=$REACT_APP_AZURE_TENANT_ID
ENV REACT_APP_AZURE_SCOPE=$REACT_APP_AZURE_SCOPE
ENV REACT_APP_API_DEV_BASE_URL=$REACT_APP_API_DEV_BASE_URL
ENV NODE_ENV=$NODE_ENV

COPY web/package.json web/package-lock.json ./
RUN npm install --legacy-peer-deps
COPY web/ ./
RUN npm run build

### --- BACKEND BUILD STAGE --- ###
FROM python:3.12-slim AS backend-build
WORKDIR /app/vehicle
COPY vehicle/pyproject.toml vehicle/poetry.lock ./
RUN pip install --no-cache-dir poetry && \
    poetry config virtualenvs.create false && \
    poetry install --no-interaction --no-ansi --no-root
COPY vehicle/ ./

### --- FINAL IMAGE --- ###
FROM python:3.12-slim
WORKDIR /app

# Install runtime dependencies including openssl for certificate extraction
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    ca-certificates \
    openssl \
    && rm -rf /var/lib/apt/lists/*

# Default: Disable SSL verification (will be enabled if emulator cert is successfully installed)
ENV PYTHONHTTPSVERIFY=0
ENV REQUESTS_CA_BUNDLE=""
ENV CURL_CA_BUNDLE=""

# Copy Python dependencies from backend-build
COPY --from=backend-build /usr/local/lib/python3.12/site-packages/ /usr/local/lib/python3.12/site-packages/
COPY --from=backend-build /usr/local/bin/ /usr/local/bin/

# Copy backend code
COPY --from=backend-build /app/vehicle ./vehicle
# Copy frontend build to backend public folder
COPY --from=frontend-build /app/web/build ./vehicle/public

# Copy entrypoint script for certificate handling
COPY docker-entrypoint.sh /usr/local/bin/
RUN chmod +x /usr/local/bin/docker-entrypoint.sh

# Expose API port
EXPOSE 8000

# Runtime environment variables (can be overridden at runtime)
ENV API_HOST=0.0.0.0
ENV API_PORT=8000
ENV PYTHONUNBUFFERED=1

# Use entrypoint to handle certificate installation
ENTRYPOINT ["/usr/local/bin/docker-entrypoint.sh"]

# Start FastAPI backend
CMD ["python", "vehicle/main.py"]