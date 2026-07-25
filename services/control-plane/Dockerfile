FROM node:22-alpine
WORKDIR /app
COPY services/control-plane/package.json .
RUN corepack enable && pnpm install --prod
COPY services/control-plane/src/ ./src/
COPY services/control-plane/tsconfig.json .
COPY packages/contracts/ ../contracts/
CMD ["npx", "tsx", "src/main.ts"]
