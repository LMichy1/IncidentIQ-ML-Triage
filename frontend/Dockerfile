# Build with context = frontend/ :
#   docker build -f frontend/Dockerfile -t incidentiq-frontend ./frontend
#
# NEXT_PUBLIC_API_BASE_URL is a *browser-facing* URL, baked into the client
# bundle at build time — it must be reachable from the user's browser, not
# from inside the Docker network. With the default docker-compose port
# mapping (backend published on localhost:8000), the default below is
# correct as-is; override the build arg if you change that mapping.
ARG NEXT_PUBLIC_API_BASE_URL=http://localhost:8000

FROM node:22-slim AS deps
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci

FROM node:22-slim AS builder
WORKDIR /app
COPY --from=deps /app/node_modules ./node_modules
COPY . .
ARG NEXT_PUBLIC_API_BASE_URL
ENV NEXT_PUBLIC_API_BASE_URL=${NEXT_PUBLIC_API_BASE_URL}
RUN npm run build

FROM node:22-slim AS runtime
WORKDIR /app
ENV NODE_ENV=production
COPY --from=builder /app/public ./public
COPY --from=builder /app/.next ./.next
COPY --from=builder /app/node_modules ./node_modules
COPY --from=builder /app/package.json ./package.json

EXPOSE 3000
CMD ["npm", "run", "start"]
