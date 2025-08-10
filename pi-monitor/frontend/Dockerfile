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
FROM nginx:alpine

# Add ARM64 support labels
LABEL architecture="arm64"
LABEL description="Pi Monitor Frontend - React Dashboard"

# Copy built app from builder stage
COPY --from=builder /app/build /usr/share/nginx/html

# Copy custom nginx configuration
COPY nginx.conf /etc/nginx/nginx.conf

# Create nginx user for security
RUN adduser -D -s /bin/sh nginx-user

# Set permissions
RUN chown -R nginx-user:nginx-user /usr/share/nginx/html
RUN chown -R nginx-user:nginx-user /var/cache/nginx
RUN chown -R nginx-user:nginx-user /var/log/nginx
RUN chown -R nginx-user:nginx-user /etc/nginx/conf.d
RUN touch /var/run/nginx.pid
RUN chown -R nginx-user:nginx-user /var/run/nginx.pid

# Switch to non-root user
USER nginx-user

# Expose port 80
EXPOSE 80

# Health check
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
  CMD wget --no-verbose --tries=1 --spider http://localhost:80/ || exit 1

# Start nginx
CMD ["nginx", "-g", "daemon off;"]
