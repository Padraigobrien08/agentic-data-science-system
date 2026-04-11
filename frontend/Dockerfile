# Production Next.js server. Build from frontend/: docker build -t edgar-web ./frontend

FROM node:22-bookworm-slim AS builder

WORKDIR /app

COPY package.json package-lock.json ./
RUN npm ci

COPY . .
RUN mkdir -p public && npm run build

FROM node:22-bookworm-slim AS runner

WORKDIR /app

ENV NODE_ENV=production \
    NEXT_TELEMETRY_DISABLED=1

# System user needs a writable home so npm/npx can cache when Next loads next.config.ts.
RUN groupadd --system --gid 1001 nodejs \
    && useradd --system --uid 1001 --gid nodejs --create-home --home-dir /home/nextjs nextjs

COPY package.json package-lock.json ./
RUN npm ci --omit=dev && npm cache clean --force

COPY --from=builder /app/.next ./.next
COPY --from=builder /app/public ./public
COPY next.config.ts postcss.config.mjs tailwind.config.ts tsconfig.json ./

RUN chown -R nextjs:nodejs /app

USER nextjs

EXPOSE 3000

# Bind on all interfaces so the container accepts external connections.
CMD ["npx", "next", "start", "-H", "0.0.0.0", "-p", "3000"]
