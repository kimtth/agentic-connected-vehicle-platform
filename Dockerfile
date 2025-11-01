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

# Copy package files for better layer caching
COPY web/package.json web/package-lock.json ./
RUN npm ci --legacy-peer-deps

# Copy source and build
COPY web/ ./
RUN npm run build && rm -rf src node_modules

### --- BACKEND BUILD STAGE --- ###
FROM python:3.12-slim AS backend-build
WORKDIR /app/vehicle

# Install poetry and configure
RUN pip install --no-cache-dir poetry==1.8.3 && \
    poetry config virtualenvs.create false

# Copy only dependency files first for better caching
COPY vehicle/pyproject.toml ./
# Copy poetry.lock if it exists (optional)
COPY vehicle/poetry.lock* ./
RUN poetry install --no-interaction --no-ansi --no-root --only main && \
    pip cache purge

# Copy application code
COPY vehicle/ ./

### --- FINAL IMAGE --- ###
FROM python:3.12-slim

# Add labels for better container management
LABEL maintainer="your-email@example.com" \
      description="Agentic Connected Car Platform" \
      version="2.0.0"

WORKDIR /app

# Install runtime dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Create non-root user for security
RUN groupadd -r appuser && useradd -r -g appuser -u 1000 appuser

# Copy Python dependencies from backend-build
COPY --from=backend-build /usr/local/lib/python3.12/site-packages/ /usr/local/lib/python3.12/site-packages/
COPY --from=backend-build /usr/local/bin/ /usr/local/bin/

# Copy backend code
COPY --from=backend-build /app/vehicle ./vehicle

# Copy frontend build to backend public folder
COPY --from=frontend-build /app/web/build ./vehicle/public

# Change ownership to non-root user
RUN chown -R appuser:appuser /app

# Switch to non-root user
USER appuser

# Expose API port
EXPOSE 8000

# Runtime environment variables (can be overridden at runtime)
ENV API_HOST=0.0.0.0 \
    API_PORT=8000 \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:8000/api/health || exit 1

# Start FastAPI backend
CMD ["python", "vehicle/main.py"]