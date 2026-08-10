use axum::{
    Router,
    body::Body,
    extract::{ConnectInfo, State},
    http::{HeaderMap, HeaderName, HeaderValue, Method, Request, StatusCode, Uri},
    response::{IntoResponse, Json, Response},
    routing::get,
};
use http_body_util::BodyExt;
use hyper_util::{
    client::legacy::Client,
    rt::{TokioExecutor, TokioTimer},
};
use serde::Serialize;
use std::{collections::HashMap, env, net::SocketAddr, str::FromStr, sync::Arc, time::Duration};
use tokio::{net::TcpListener, sync::Mutex, time::Instant};
use tower_http::{
    catch_panic::CatchPanicLayer, cors::CorsLayer, limit::RequestBodyLimitLayer,
    request_id::MakeRequestUuid, set_header::SetResponseHeaderLayer, trace::TraceLayer,
};
use tracing::{info, warn};
use tracing_subscriber::EnvFilter;
use uuid::Uuid;

// ── Rate Limiter ──────────────────────────

const DEFAULT_RATE_LIMIT_WINDOW_SECS: u64 = 60;
const DEFAULT_RATE_LIMIT_MAX_REQUESTS: u32 = 120;

#[derive(Clone)]
struct RateLimiter {
    window: Duration,
    max_requests: u32,
    clients: Arc<Mutex<HashMap<String, (Instant, u32)>>>,
}

impl RateLimiter {
    fn new(window_secs: u64, max_requests: u32) -> Self {
        Self {
            window: Duration::from_secs(window_secs),
            max_requests,
            clients: Arc::new(Mutex::new(HashMap::new())),
        }
    }

    async fn check(&self, client_ip: &str) -> (bool, u64) {
        let mut guard = self.clients.lock().await;
        let now = Instant::now();

        if let Some((start, count)) = guard.get_mut(client_ip) {
            let elapsed = now.duration_since(*start);
            if elapsed > self.window {
                *start = now;
                *count = 1;
                return (true, 0);
            }
            if *count >= self.max_requests {
                let remaining = self.window.saturating_sub(elapsed);
                let retry_after = remaining.as_secs().max(1);
                return (false, retry_after);
            }
            *count += 1;
            (true, 0)
        } else {
            guard.insert(client_ip.to_string(), (now, 1));
            (true, 0)
        }
    }
}

// ── Application State ─────────────────────

struct AppState {
    client: Client<hyper_util::client::legacy::connect::HttpConnector, axum::body::Body>,
    control_plane_url: String,
    reasoning_engine_url: String,
    observability_url: String,
    service_secret: String,
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

async fn live(headers: HeaderMap) -> Json<HealthResponse> {
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
    } else if path.starts_with("/api/observability") {
        format!(
            "{}{}",
            state.observability_url,
            path.replacen("/api/observability", "", 1)
        )
    } else if path.starts_with("/health") {
        return Ok((
            StatusCode::OK,
            [(
                HeaderName::from_static("x-request-id"),
                HeaderValue::from_str(&request_id)
                    .unwrap_or_else(|_| HeaderValue::from_static("invalid")),
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

    let (_parts, body) = req.into_parts();
    let body_bytes = body
        .collect()
        .await
        .map_err(|_| StatusCode::BAD_REQUEST)?
        .to_bytes();

    let upstream_req = Request::builder()
        .method(method)
        .uri(uri)
        .header("x-request-id", &request_id)
        .header("x-service-secret", &state.service_secret)
        .header(
            "x-forwarded-for",
            headers
                .get("x-forwarded-for")
                .and_then(|v| v.to_str().ok())
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

    for (key, value) in resp_headers.iter() {
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
        .filter(|s| !s.is_empty())
        .map(|s| s.to_string())
        .unwrap_or_else(|| Uuid::new_v4().to_string())
}

async fn rate_limit_middleware(
    State(limiter): State<RateLimiter>,
    ConnectInfo(addr): ConnectInfo<SocketAddr>,
    req: Request<Body>,
    next: axum::middleware::Next,
) -> Response {
    let client_ip = req
        .headers()
        .get("x-forwarded-for")
        .and_then(|v| v.to_str().ok())
        .and_then(|s| s.split(',').next())
        .map(|s| s.trim().to_string())
        .unwrap_or_else(|| addr.ip().to_string());

    let (allowed, retry_after) = limiter.check(&client_ip).await;
    if !allowed {
        return (
            StatusCode::TOO_MANY_REQUESTS,
            [(
                HeaderName::from_static("retry-after"),
                HeaderValue::from_str(&retry_after.to_string())
                    .unwrap_or_else(|_| HeaderValue::from_static("60")),
            )],
            Json(serde_json::json!({"error":"rate limit exceeded"})),
        )
            .into_response();
    }

    next.run(req).await
}

async fn cleanup_rate_limiter(limiter: RateLimiter) {
    let mut interval = tokio::time::interval(Duration::from_secs(300));
    interval.set_missed_tick_behavior(tokio::time::MissedTickBehavior::Skip);
    loop {
        interval.tick().await;
        let mut guard = limiter.clients.lock().await;
        let now = Instant::now();
        guard.retain(|_, (start, _)| now.duration_since(*start) <= limiter.window);
    }
}

// ── Main ──────────────────────────────────

#[tokio::main]
async fn main() -> Result<(), Box<dyn std::error::Error>> {
    init_tracing();

    let control_plane_url =
        env::var("CONTROL_PLANE_URL").unwrap_or_else(|_| "http://localhost:8100".to_owned());
    let reasoning_engine_url =
        env::var("REASONING_ENGINE_URL").unwrap_or_else(|_| "http://localhost:8200".to_owned());
    let observability_url =
        env::var("OBSERVABILITY_URL").unwrap_or_else(|_| "http://localhost:8500".to_owned());
    let service_secret =
        env::var("SERVICE_SECRET").unwrap_or_else(|_| String::new());
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
        observability_url: observability_url.trim_end_matches('/').to_owned(),
        service_secret,
        request_limit_bytes,
    });

    let host = env::var("KAGENT_HTTP_HOST").unwrap_or_else(|_| "127.0.0.1".to_owned());
    let port = parse_port(&env::var("KAGENT_GATEWAY_PORT").unwrap_or_else(|_| "8080".to_owned()))?;
    let address: SocketAddr = format!("{host}:{port}").parse()?;

    let cors = CorsLayer::new()
        .allow_origin(tower_http::cors::Any)
        .allow_methods([Method::GET, Method::POST, Method::PATCH, Method::DELETE])
        .allow_headers(tower_http::cors::Any);

    let rate_limit_window_secs: u64 = env::var("GATEWAY_RATE_LIMIT_WINDOW_SECONDS")
        .ok()
        .and_then(|v| v.parse().ok())
        .unwrap_or(DEFAULT_RATE_LIMIT_WINDOW_SECS);
    let rate_limit_max_requests: u32 = env::var("GATEWAY_RATE_LIMIT_MAX_REQUESTS")
        .ok()
        .and_then(|v| v.parse().ok())
        .unwrap_or(DEFAULT_RATE_LIMIT_MAX_REQUESTS);

    let limiter = RateLimiter::new(rate_limit_window_secs, rate_limit_max_requests);
    tokio::spawn(cleanup_rate_limiter(limiter.clone()));

    let app = Router::new()
        .route("/health/live", get(live))
        .route_layer(axum::middleware::from_fn_with_state(
            limiter.clone(),
            rate_limit_middleware,
        ))
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
        .layer(CatchPanicLayer::new())
        .with_state(state.clone());

    let listener = TcpListener::bind(address).await?;
    info!(%address, control_plane_url = %control_plane_url, reasoning_engine_url = %reasoning_engine_url, observability_url = %observability_url, "gateway_started");
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
    use super::*;

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

    #[test]
    fn get_request_id_absent_generates_uuid() {
        let headers = HeaderMap::new();
        let id = get_request_id(&headers);
        assert!(!id.is_empty());
        assert!(Uuid::parse_str(&id).is_ok());
    }

    #[test]
    fn get_request_id_empty_generates_uuid() {
        let mut headers = HeaderMap::new();
        headers.insert("x-request-id", HeaderValue::from_static(""));
        let id = get_request_id(&headers);
        assert!(!id.is_empty());
        assert!(Uuid::parse_str(&id).is_ok());
    }

    #[test]
    fn get_request_id_present_returns_value() {
        let mut headers = HeaderMap::new();
        headers.insert("x-request-id", HeaderValue::from_static("test-req-123"));
        let id = get_request_id(&headers);
        assert_eq!(id, "test-req-123");
    }

    #[tokio::test]
    async fn rate_limiter_allows_under_limit() {
        let limiter = RateLimiter::new(60, 2);
        let (allowed1, _) = limiter.check("127.0.0.1").await;
        let (allowed2, _) = limiter.check("127.0.0.1").await;
        assert!(allowed1);
        assert!(allowed2);
    }

    #[tokio::test]
    async fn rate_limiter_blocks_over_limit_with_retry_after() {
        let limiter = RateLimiter::new(60, 2);
        limiter.check("127.0.0.1").await;
        limiter.check("127.0.0.1").await;
        let (allowed, retry_after) = limiter.check("127.0.0.1").await;
        assert!(!allowed);
        assert!(retry_after > 0 && retry_after <= 60);
    }

    #[tokio::test]
    async fn rate_limiter_resets_after_window() {
        let limiter = RateLimiter::new(1, 1);
        let (allowed1, _) = limiter.check("127.0.0.1").await;
        assert!(allowed1);
        let (allowed2, _) = limiter.check("127.0.0.1").await;
        assert!(!allowed2);

        tokio::time::sleep(Duration::from_millis(1100)).await;
        let (allowed3, _) = limiter.check("127.0.0.1").await;
        assert!(allowed3);
    }

    #[tokio::test]
    async fn rate_limiter_cleanup_evicts_expired_clients() {
        let limiter = RateLimiter::new(1, 5);
        limiter.check("127.0.0.1").await;
        assert_eq!(limiter.clients.lock().await.len(), 1);

        tokio::time::sleep(Duration::from_millis(1100)).await;

        let now = Instant::now();
        limiter
            .clients
            .lock()
            .await
            .retain(|_, (start, _)| now.duration_since(*start) <= limiter.window);
        assert_eq!(limiter.clients.lock().await.len(), 0);
    }
}
