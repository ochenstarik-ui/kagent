use axum::{
    Router,
    body::Body,
    extract::State,
    http::{HeaderMap, HeaderName, HeaderValue, Method, Request, StatusCode, Uri},
    response::{IntoResponse, Json, Response},
    routing::get,
};
use http_body_util::BodyExt;
use hyper_util::{
    client::legacy::{Client, connect::HttpConnector},
    rt::{TokioExecutor, TokioTimer},
};
use serde::Serialize;
use std::{env, net::SocketAddr, str::FromStr, sync::Arc, time::Duration};
use tokio::net::TcpListener;
use tower_http::{
    cors::CorsLayer, limit::RequestBodyLimitLayer, request_id::MakeRequestUuid,
    set_header::SetResponseHeaderLayer, trace::TraceLayer,
};
use tracing::{info, warn};
use tracing_subscriber::EnvFilter;
use uuid::Uuid;

// ── Application State ─────────────────────

struct AppState {
    client: Client<HttpConnector, Body>,
    control_plane_url: String,
    reasoning_engine_url: String,
    request_limit_bytes: usize,
}

// ── Health ────────────────────────────────

#[derive(Serialize)]
struct HealthResponse {
    status: &'static str,
    service: &'static str,
    version: &'static str,
    request_id: String,
}

async fn live(State(_state): State<Arc<AppState>>, headers: HeaderMap) -> Json<HealthResponse> {
    let request_id = get_request_id(&headers);
    Json(HealthResponse {
        status: "ok",
        service: "gateway",
        version: "0.2.0",
        request_id,
    })
}

// ── Reverse Proxy ─────────────────────────

async fn proxy(
    State(state): State<Arc<AppState>>,
    req: Request<Body>,
) -> Result<Response, StatusCode> {
    let path = req.uri().path();
    let method = req.method().clone();
    let headers = req.headers().clone();
    let request_id = get_request_id(&headers);

    // Route to internal service
    let backend_url = if path.starts_with("/api/control-plane") {
        format!(
            "{}{}",
            state.control_plane_url,
            path.replacen("/api/control-plane", "", 1)
        )
    } else if path.starts_with("/api/reasoning") {
        format!(
            "{}{}",
            state.reasoning_engine_url,
            path.replacen("/api/reasoning", "", 1)
        )
    } else if path.starts_with("/health") {
        return Ok((
            StatusCode::OK,
            [(
                HeaderName::from_static("x-request-id"),
                HeaderValue::from_str(&request_id)
                    .expect("request ID must be a valid header value"),
            )],
            Json(serde_json::json!({"status":"ok","service":"gateway","proxy":true}))
                .into_response(),
        )
            .into_response());
    } else {
        return Err(StatusCode::NOT_FOUND);
    };

    // Build upstream request
    let uri = Uri::from_str(&backend_url).map_err(|e| {
        warn!(%e, "Invalid backend URI");
        StatusCode::BAD_GATEWAY
    })?;

    let body = req.into_body();
    let body_bytes = body
        .collect()
        .await
        .map_err(|_| StatusCode::BAD_REQUEST)?
        .to_bytes();

    let upstream_req = Request::builder()
        .method(method)
        .uri(uri)
        .header("x-request-id", &request_id)
        .header(
            "x-forwarded-for",
            headers
                .get("x-forwarded-for")
                .map(|v| v.to_str().unwrap_or("unknown"))
                .unwrap_or("unknown"),
        )
        .body(Body::from(body_bytes))
        .map_err(|_| StatusCode::BAD_GATEWAY)?;

    // Forward
    let resp = state.client.request(upstream_req).await.map_err(|e| {
        warn!(%e, "Backend unreachable");
        StatusCode::BAD_GATEWAY
    })?;

    // Copy response
    let status = resp.status();
    let resp_headers = resp.headers().clone();
    let resp_body = resp
        .into_body()
        .collect()
        .await
        .map_err(|_| StatusCode::BAD_GATEWAY)?
        .to_bytes();

    let mut response = Response::builder()
        .status(status)
        .header("x-request-id", &request_id)
        .body(Body::from(resp_body))
        .map_err(|_| StatusCode::INTERNAL_SERVER_ERROR)?;

    for (key, value) in &resp_headers {
        if key != "transfer-encoding" && key != "content-encoding" {
            response.headers_mut().insert(key, value.clone());
        }
    }

    Ok(response)
}

// ── Helpers ───────────────────────────────

fn get_request_id(headers: &HeaderMap) -> String {
    headers
        .get("x-request-id")
        .and_then(|v| v.to_str().ok())
        .filter(|value| !value.is_empty())
        .map(str::to_owned)
        .unwrap_or_else(|| Uuid::new_v4().to_string())
}

// ── Main ──────────────────────────────────

#[tokio::main]
async fn main() -> Result<(), Box<dyn std::error::Error>> {
    init_tracing();

    let control_plane_url =
        env::var("CONTROL_PLANE_URL").unwrap_or_else(|_| "http://localhost:8100".to_owned());
    let reasoning_engine_url =
        env::var("REASONING_ENGINE_URL").unwrap_or_else(|_| "http://localhost:8200".to_owned());
    let request_limit_bytes: usize = env::var("GATEWAY_REQUEST_LIMIT_BYTES")
        .unwrap_or_else(|_| "10485760".to_owned())
        .parse()
        .unwrap_or(10 * 1024 * 1024); // 10 MB

    let state = Arc::new(AppState {
        client: Client::builder(TokioExecutor::new())
            .timer(TokioTimer::new())
            .pool_idle_timeout(Duration::from_secs(30))
            .build_http(),
        control_plane_url: control_plane_url.trim_end_matches('/').to_owned(),
        reasoning_engine_url: reasoning_engine_url.trim_end_matches('/').to_owned(),
        request_limit_bytes,
    });

    let host = env::var("KAGENT_HTTP_HOST").unwrap_or_else(|_| "127.0.0.1".to_owned());
    let port = parse_port(&env::var("KAGENT_GATEWAY_PORT").unwrap_or_else(|_| "8080".to_owned()))?;
    let address: SocketAddr = format!("{host}:{port}").parse()?;

    let cors = CorsLayer::new()
        .allow_origin(tower_http::cors::Any)
        .allow_methods([Method::GET, Method::POST, Method::PATCH, Method::DELETE])
        .allow_headers(tower_http::cors::Any);

    let app = Router::new()
        .route("/health/live", get(live))
        .fallback(proxy)
        .layer(SetResponseHeaderLayer::overriding(
            HeaderName::from_static("x-content-type-options"),
            HeaderValue::from_static("nosniff"),
        ))
        .layer(SetResponseHeaderLayer::overriding(
            HeaderName::from_static("x-frame-options"),
            HeaderValue::from_static("DENY"),
        ))
        .layer(RequestBodyLimitLayer::new(state.request_limit_bytes))
        .layer(cors)
        .layer(TraceLayer::new_for_http())
        .layer(tower_http::request_id::SetRequestIdLayer::new(
            HeaderName::from_static("x-request-id"),
            MakeRequestUuid,
        ))
        .with_state(state);

    let listener = TcpListener::bind(address).await?;
    info!(%address, control_plane_url = %control_plane_url, reasoning_engine_url = %reasoning_engine_url, "gateway_started");
    axum::serve(listener, app)
        .with_graceful_shutdown(shutdown_signal())
        .await?;

    Ok(())
}

fn parse_port(value: &str) -> Result<u16, String> {
    value
        .parse::<u16>()
        .map_err(|_| format!("invalid KAGENT_GATEWAY_PORT: {value}"))
        .and_then(|port| {
            if port == 0 {
                Err("KAGENT_GATEWAY_PORT must be greater than zero".to_owned())
            } else {
                Ok(port)
            }
        })
}

fn init_tracing() {
    let filter = EnvFilter::try_from_default_env()
        .unwrap_or_else(|_| EnvFilter::new("kagent_gateway=info,tower_http=info"));

    tracing_subscriber::fmt()
        .with_env_filter(filter)
        .json()
        .init();
}

async fn shutdown_signal() {
    let ctrl_c = async {
        tokio::signal::ctrl_c()
            .await
            .expect("failed to install Ctrl+C handler");
    };

    #[cfg(unix)]
    let terminate = async {
        tokio::signal::unix::signal(tokio::signal::unix::SignalKind::terminate())
            .expect("failed to install SIGTERM handler")
            .recv()
            .await;
    };

    #[cfg(not(unix))]
    let terminate = std::future::pending::<()>();

    tokio::select! {
        () = ctrl_c => {},
        () = terminate => {},
    }

    info!("gateway_shutdown_requested");
}

#[cfg(test)]
mod tests {
    use super::parse_port;

    #[test]
    fn parses_valid_port() {
        assert_eq!(parse_port("8080"), Ok(8080));
    }

    #[test]
    fn rejects_zero_and_invalid_ports() {
        assert!(parse_port("0").is_err());
        assert!(parse_port("70000").is_err());
        assert!(parse_port("abc").is_err());
    }
}
