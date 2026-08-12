FROM node:22-alpine
WORKDIR /app
RUN corepack enable
COPY package.json pnpm-lock.yaml pnpm-workspace.yaml tsconfig.base.json ./
COPY packages/contracts/package.json ./packages/contracts/
COPY services/control-plane/package.json ./services/control-plane/
RUN pnpm install --frozen-lockfile
COPY packages/contracts/ ./packages/contracts/
COPY services/control-plane/ ./services/control-plane/
RUN pnpm --filter @kagent/contracts build && pnpm --filter @kagent/control-plane build
CMD ["node", "services/control-plane/dist/main.js"]
