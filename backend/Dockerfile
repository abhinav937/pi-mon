# Pi Monitor Backend - Enhanced Docker Container for Pi Monitoring
# Optimized for Raspberry Pi deployment

FROM python:3.11-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=5001

# Set working directory
WORKDIR /app

# Install essential system dependencies for Pi monitoring
RUN apt-get update && apt-get install -y \
    curl \
    gcc \
    python3-dev \
    procps \
    sysstat \
    iproute2 \
    net-tools \
    lsof \
    htop \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the server and config files
COPY backend/simple_server.py .
COPY config.py .

# Create a simple startup script
RUN echo '#!/bin/bash\npython simple_server.py' > start.sh && chmod +x start.sh

# Expose port
EXPOSE 5001

# Health check - simple HTTP check
HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
  CMD curl -f http://localhost:5001/health || exit 1

# Run the server
CMD ["./start.sh"]
