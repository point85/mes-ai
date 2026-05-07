# Design-Time Client (DT) — Docker image
#
# Build context: clients/   (set in root docker-compose.yml)
# The context root gives access to mes.config.json (required by vite.config.ts).

# ── Stage 1: build ─────────────────────────────────────────────────────────
FROM node:20-alpine AS builder

WORKDIR /app/design_time

# mes.config.json is one level above the client dir; vite.config.ts requires '../mes.config.json'
COPY mes.config.json /app/mes.config.json

# Install dependencies (cached separately from source)
COPY design_time/package*.json ./
RUN npm install --no-audit --no-fund

# Copy source and build
COPY design_time/ ./
RUN npm run build

# ── Stage 2: serve ─────────────────────────────────────────────────────────
FROM nginx:alpine

COPY --from=builder /app/design_time/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
