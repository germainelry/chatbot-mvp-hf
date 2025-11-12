# Multi-stage build for production optimization
FROM python:3.11-slim as builder

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt

# Production stage
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Copy Python dependencies from builder
COPY --from=builder /root/.local /root/.local

# Make sure scripts in .local are usable
ENV PATH=/root/.local/bin:$PATH

# Copy application code
COPY . .

# Create directories for uploads and chroma_db
RUN mkdir -p uploads chroma_db

# Expose port (Railway will set PORT env var)
EXPOSE 8000

# Use gunicorn with uvicorn workers for production
CMD gunicorn app.main:app -w 4 -k uvicorn.workers.UvicornWorker -b 0.0.0.0:${PORT:-8000} --timeout 120

