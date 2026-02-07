# Stage 1: Dependencies
FROM node:20-alpine AS deps
WORKDIR /app

# Copy package files
COPY package.json package-lock.json* ./

# Install dependencies with cache mount for faster rebuilds
RUN --mount=type=cache,target=/root/.npm \
    npm ci

# Stage 2: Development
FROM node:20-alpine AS development
WORKDIR /app

# Create a non-privileged user for security
# See https://docs.docker.com/go/dockerfile-user-best-practices/
ARG UID=10001
RUN adduser \
    --disabled-password \
    --gecos "" \
    --home "/nonexistent" \
    --shell "/sbin/nologin" \
    --no-create-home \
    --uid "${UID}" \
    appuser

# Copy dependencies from deps stage (as root first)
COPY --from=deps /app/node_modules ./node_modules
COPY . .

# Create .next directory and fix all permissions for appuser
RUN mkdir -p .next && chown -R appuser:appuser /app

# Switch to non-privileged user
USER appuser

# Expose port
EXPOSE 3000

# Set environment for development
ENV NODE_ENV=development
ENV NEXT_TELEMETRY_DISABLED=1

# Run development server with hot-reload
CMD ["npm", "run", "dev"]

