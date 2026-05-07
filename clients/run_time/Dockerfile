# Run-Time Client (RT) — Docker image
#
# Build context: clients/   (set in root docker-compose.yml)

# ── Stage 1: build ─────────────────────────────────────────────────────────
FROM node:20-alpine AS builder

WORKDIR /app/run_time

COPY mes.config.json /app/mes.config.json

COPY run_time/package*.json ./
RUN npm install --no-audit --no-fund

COPY run_time/ ./
RUN npm run build

# ── Stage 2: serve ─────────────────────────────────────────────────────────
FROM nginx:alpine

COPY --from=builder /app/run_time/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
