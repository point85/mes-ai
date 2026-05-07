# Equipment Simulator — Docker image
#
# Build context: clients/   (set in root docker-compose.yml)

# ── Stage 1: build ─────────────────────────────────────────────────────────
FROM node:20-alpine AS builder

WORKDIR /app/equipment_simulator

COPY mes.config.json /app/mes.config.json

COPY equipment_simulator/package*.json ./
RUN npm ci

COPY equipment_simulator/ ./
RUN npm run build

# ── Stage 2: serve ─────────────────────────────────────────────────────────
FROM nginx:alpine

COPY --from=builder /app/equipment_simulator/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
