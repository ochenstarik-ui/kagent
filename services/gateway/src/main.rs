use axum::{Json, Router, routing::get};
use serde::Serialize;
use std::{env, net::SocketAddr};
use tokio::net::TcpListener;
use tower_http::{request_id::MakeRequestUuid, trace::TraceLayer};
use tracing::info;
use tracing_subscriber::EnvFilter;

#[derive(Serialize)]
struct HealthResponse {
    status: &'static str,
    service: &'static str,
}

#[tokio::main]
async fn main() -> Result<(), Box<dyn std::error::Error>> {
    init_tracing();

    let host = env::var("KAGENT_HTTP_HOST").unwrap_or_else(|_| "127.0.0.1".to_owned());
    let port = parse_port(
        &env::var("KAGENT_GATEWAY_PORT").unwrap_or_else(|_| "8080".to_owned()),
    )?;
    let address: SocketAddr = format!("{host}:{port}").parse()?;

    let app = Router::new()
        .route("/health/live", get(live))
        .layer(TraceLayer::new_for_http())
        .layer(tower_http::request_id::SetRequestIdLayer::new(
            axum::http::HeaderName::from_static("x-request-id"),
            MakeRequestUuid,
        ));

    let listener = TcpListener::bind(address).await?;
    info!(%address, "gateway_started");
    axum::serve(listener, app)
        .with_graceful_shutdown(shutdown_signal())
        .await?;

    Ok(())
}

async fn live() -> Json<HealthResponse> {
    Json(HealthResponse {
        status: "ok",
        service: "gateway",
    })
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
