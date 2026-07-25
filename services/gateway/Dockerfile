FROM rust:1.88-slim AS builder
WORKDIR /app
COPY services/gateway/Cargo.toml services/gateway/Cargo.lock* ./
RUN mkdir src && echo "fn main() {}" > src/main.rs && cargo build --release 2>/dev/null; rm -rf src
COPY services/gateway/src/ ./src/
RUN cargo build --release

FROM debian:bookworm-slim
RUN apt-get update && apt-get install -y ca-certificates && rm -rf /var/lib/apt/lists/*
COPY --from=builder /app/target/release/kagent-gateway /usr/local/bin/gateway
EXPOSE 8080
CMD ["gateway"]
