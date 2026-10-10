# Production image for the Nuxt SSR frontend. Build context: repository root.
# Runtime config (NUXT_PUBLIC_API_BASE, NUXT_PUBLIC_SITE_URL) is read from the environment at start.
FROM node:22-slim AS build
WORKDIR /app
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci --no-audit --no-fund
COPY frontend/ .
ENV NODE_OPTIONS=--max-old-space-size=1536
RUN npm run build

FROM node:22-slim
WORKDIR /app
COPY --from=build /app/.output .output
ENV NODE_ENV=production HOST=0.0.0.0 PORT=3000
USER node
EXPOSE 3000
CMD ["node", ".output/server/index.mjs"]
