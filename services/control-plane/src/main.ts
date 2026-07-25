/** KAgent Control Plane — Fastify server entry point. */

import Fastify from "fastify";
import { Pool } from "pg";
import { registerRoutes } from "./routes.js";
import { registerAuthRoutes } from "./auth-routes.js";

const app = Fastify({
  logger: {
    transport: {
      target: "pino-pretty",
      options: { colorize: false, translateTime: "HH:MM:ss" },
    },
  },
});

// Database pool
const pool = new Pool({
  connectionString: process.env["DATABASE_URL"] ?? "postgres://kagent:change-me-locally@127.0.0.1:5432/kagent",
  max: 10,
});

// Register API routes
await registerRoutes(app);
await registerAuthRoutes(app, pool);

// Start
const port = parseInt(process.env["CONTROL_PLANE_PORT"] ?? "8100", 10);
const host = process.env["CONTROL_PLANE_HOST"] ?? "0.0.0.0";

try {
  await app.listen({ port, host });
  console.log(
    JSON.stringify({
      level: "info",
      service: "control-plane",
      message: "server_started",
      host,
      port,
      version: "0.2.0",
    })
  );
} catch (err) {
  app.log.error(err);
  process.exit(1);
}

// Graceful shutdown
async function shutdown(signal: string) {
  console.log(JSON.stringify({ level: "info", service: "control-plane", message: "shutdown", signal }));
  await app.close();
  process.exit(0);
}

process.on("SIGINT", () => shutdown("SIGINT"));
process.on("SIGTERM", () => shutdown("SIGTERM"));
