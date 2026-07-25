import { loadConfig } from "./config.js";
import { createControlPlaneServer } from "./server.js";

const config = loadConfig();
const server = createControlPlaneServer();

server.listen(config.port, config.host, () => {
  console.log(
    JSON.stringify({
      level: "info",
      service: "control-plane",
      message: "server_started",
      host: config.host,
      port: config.port
    })
  );
});

function shutdown(signal: string): void {
  console.log(
    JSON.stringify({
      level: "info",
      service: "control-plane",
      message: "shutdown_requested",
      signal
    })
  );
  server.close((error) => {
    if (error) {
      console.error(error);
      process.exitCode = 1;
    }
  });
}

process.once("SIGINT", () => shutdown("SIGINT"));
process.once("SIGTERM", () => shutdown("SIGTERM"));
