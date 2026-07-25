import { createServer, type IncomingMessage, type ServerResponse } from "node:http";

export function createControlPlaneServer() {
  return createServer((request, response) => {
    route(request, response);
  });
}

function route(request: IncomingMessage, response: ServerResponse): void {
  const requestId = request.headers["x-request-id"] ?? crypto.randomUUID();
  response.setHeader("content-type", "application/json; charset=utf-8");
  response.setHeader("x-request-id", requestId);

  if (request.method === "GET" && request.url === "/health/live") {
    sendJson(response, 200, {
      status: "ok",
      service: "control-plane"
    });
    return;
  }

  if (request.method === "GET" && request.url === "/v1/system/info") {
    sendJson(response, 200, {
      name: "KAgent Control Plane",
      version: "0.1.0-dev",
      apiVersion: "v1"
    });
    return;
  }

  sendJson(response, 404, {
    code: "not_found",
    message: "Route not found"
  });
}

function sendJson(
  response: ServerResponse,
  statusCode: number,
  body: unknown
): void {
  response.statusCode = statusCode;
  response.end(JSON.stringify(body));
}
