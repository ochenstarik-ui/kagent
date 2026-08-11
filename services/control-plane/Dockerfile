# Build stage: resolve the workspace, build contracts, then the service.
#
# The previous version copied only services/control-plane/package.json and ran
# `pnpm install --prod` against it. That cannot work: the manifest declares
# "@kagent/contracts": "workspace:*", and outside a workspace pnpm has nothing to
# resolve it against. The image had never been built until the end-to-end job
# tried to start the stack.
FROM node:22-alpine AS build
WORKDIR /repo
RUN corepack enable

COPY pnpm-workspace.yaml package.json tsconfig.base.json ./
COPY packages/contracts/package.json packages/contracts/
COPY services/control-plane/package.json services/control-plane/
RUN pnpm install --frozen-lockfile=false

COPY packages/contracts/ packages/contracts/
COPY services/control-plane/ services/control-plane/
RUN pnpm --filter @kagent/contracts build \
 && pnpm --filter @kagent/control-plane build

# Runtime stage: production dependencies and compiled output only.
FROM node:22-alpine AS runtime
WORKDIR /repo
RUN corepack enable
ENV NODE_ENV=production

COPY pnpm-workspace.yaml package.json ./
COPY packages/contracts/package.json packages/contracts/
COPY services/control-plane/package.json services/control-plane/
RUN pnpm install --prod --frozen-lockfile=false

COPY --from=build /repo/packages/contracts/dist packages/contracts/dist
COPY --from=build /repo/services/control-plane/dist services/control-plane/dist

WORKDIR /repo/services/control-plane
CMD ["node", "dist/main.js"]
