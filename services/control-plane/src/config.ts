export interface ControlPlaneConfig {
  readonly host: string;
  readonly port: number;
}

export function loadConfig(
  env: NodeJS.ProcessEnv = process.env
): ControlPlaneConfig {
  return {
    host: env.KAGENT_HTTP_HOST ?? "127.0.0.1",
    port: parsePort(env.KAGENT_CONTROL_PLANE_PORT ?? "8081")
  };
}

function parsePort(value: string): number {
  const port = Number.parseInt(value, 10);
  if (!Number.isInteger(port) || port < 1 || port > 65535) {
    throw new Error(`Invalid TCP port: ${value}`);
  }
  return port;
}
