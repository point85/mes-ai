# ERP Simulator — Docker image
#
# Build context: clients/   (set in root docker-compose.yml)

# ── Stage 1: build ─────────────────────────────────────────────────────────
FROM node:20-alpine AS builder

WORKDIR /app/erp_simulator

COPY mes.config.json /app/mes.config.json

COPY erp_simulator/package*.json ./
RUN npm install --no-audit --no-fund

COPY erp_simulator/ ./
RUN npm run build

# ── Stage 2: serve ─────────────────────────────────────────────────────────
FROM nginx:alpine

COPY --from=builder /app/erp_simulator/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
