# Pi Monitor Backend - Dockerfile for ARM64 support

FROM python:3.11-slim

# Add ARM64 support labels
LABEL architecture="arm64"
LABEL description="Pi Monitor Backend - FastAPI Server"

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    libc6-dev \
    libffi-dev \
    libssl-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user
RUN adduser --disabled-password --gecos '' --uid 1000 appuser

# Copy requirements first for better caching
COPY requirements.txt .

# Create virtual environment
RUN python -m venv /app/venv

# Activate virtual environment and install dependencies
RUN /app/venv/bin/pip install --no-cache-dir --upgrade pip \
    && /app/venv/bin/pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Change ownership to appuser (including venv)
RUN chown -R appuser:appuser /app

# Switch to non-root user
USER appuser

# Create logs directory
RUN mkdir -p /app/logs

# Expose port
EXPOSE 5000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
  CMD curl -f http://localhost:5000/health || exit 1

# Run the application using venv
CMD ["/app/venv/bin/uvicorn", "main_server:combined_app", "--host", "0.0.0.0", "--port", "5000", "--workers", "1"]
