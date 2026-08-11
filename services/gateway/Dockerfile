# The previous version pre-built a dummy `fn main() {}` to cache dependency
# layers, then copied the real sources over it. Cargo kept the stale artifact,
# so the image shipped the dummy binary: the container started and exited with
# code 0 immediately, and every dependent service failed to start behind it.
#
# The trick is dropped. Correctness first; dependency caching can come back
# later through a cache mount, which does not risk shipping the wrong binary.
FROM rust:1.88-slim AS builder
WORKDIR /app
COPY services/gateway/Cargo.toml services/gateway/Cargo.lock* ./
COPY services/gateway/src/ ./src/
RUN cargo build --release

FROM debian:bookworm-slim
RUN apt-get update && apt-get install -y ca-certificates && rm -rf /var/lib/apt/lists/*
COPY --from=builder /app/target/release/kagent-gateway /usr/local/bin/gateway
EXPOSE 8080
CMD ["gateway"]
