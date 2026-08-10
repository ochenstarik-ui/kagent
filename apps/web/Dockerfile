FROM node:22-alpine AS base

# 1. Install dependencies
FROM base AS install
WORKDIR /app
# Enable corepack for pnpm
RUN corepack enable pnpm

# Copy root configurations
COPY package.json pnpm-lock.yaml pnpm-workspace.yaml ./
# Copy workspace packages package.json (if any dependencies exist, but here we just need web)
COPY apps/web/package.json ./apps/web/

# Install dependencies specifically for web
RUN pnpm install --filter @kagent/web...

# 2. Build the app
FROM base AS build
WORKDIR /app
RUN corepack enable pnpm
COPY --from=install /app/node_modules ./node_modules
COPY --from=install /app/apps/web/node_modules ./apps/web/node_modules
# Copy all source files
COPY . .
# Build web
RUN pnpm --filter @kagent/web build

# 3. Production image
FROM base AS production
WORKDIR /app
ENV NODE_ENV=production

# Copy standalone output
COPY --from=build /app/apps/web/.next/standalone ./
COPY --from=build /app/apps/web/public ./apps/web/public
COPY --from=build /app/apps/web/.next/static ./apps/web/.next/static

EXPOSE 3000
ENV PORT=3000
ENV HOSTNAME="0.0.0.0"

# Note: standalone mode in a monorepo creates server.js inside apps/web/
CMD ["node", "apps/web/server.js"]
