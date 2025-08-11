# Pi Monitor Frontend - Multi-stage Dockerfile for ARM64 support

# Build stage
FROM node:18-alpine AS builder

# Set working directory
WORKDIR /app

# Copy package files
COPY package.json package-lock.json* ./

# Install dependencies (including devDependencies for build)
# Use npm install if package-lock.json doesn't exist, otherwise use npm ci
RUN if [ -f package-lock.json ]; then \
      npm ci --silent; \
    else \
      npm install --silent; \
    fi && \
    npm cache clean --force

# Copy public directory first (required for React build)
COPY public/ ./public/

# Copy source code
COPY src/ ./src/
COPY tailwind.config.js ./

# Build the React app
RUN npm run build

# Production stage
FROM httpd:alpine

# Add ARM64 support labels
LABEL architecture="arm64"
LABEL description="Pi Monitor Frontend - React Dashboard"

# Install wget for health checks and curl for backend connectivity testing
RUN apk add --no-cache wget curl

# Copy built app from builder stage
COPY --from=builder /app/build /usr/local/apache2/htdocs

# Copy custom nginx configuration
COPY httpd.conf /usr/local/apache2/conf/httpd.conf

# Copy startup script
COPY startup.sh /startup.sh
RUN chmod +x /startup.sh

# Expose port 80
EXPOSE 80

# Health check
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
  CMD wget --no-verbose --tries=1 --spider http://localhost:80/ || exit 1

# Start with our custom startup script
CMD ["/startup.sh"]
