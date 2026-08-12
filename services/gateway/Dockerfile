# The original version pre-built a dummy `fn main() {}` to cache dependency
# layers, then copied the real sources over it. Cargo kept the stale artifact,
# so the image shipped the dummy binary: the container started and exited with
# code 0, and every service depending on gateway health failed to come up.
#
# The trick is dropped. Correctness first; dependency caching can return later
# through a cache mount, which cannot ship the wrong binary.
FROM rust:1.88-slim AS builder
WORKDIR /app
COPY services/gateway/Cargo.toml services/gateway/Cargo.lock* ./
COPY services/gateway/src/ ./src/
RUN cargo build --release

FROM debian:bookworm-slim
# wget is required by the compose healthcheck. Without it the probe fails with
# "executable not found", the container is reported unhealthy, and dependants
# never start.
RUN apt-get update \
 && apt-get install -y --no-install-recommends ca-certificates wget \
 && rm -rf /var/lib/apt/lists/*
COPY --from=builder /app/target/release/kagent-gateway /usr/local/bin/gateway
EXPOSE 8080
CMD ["gateway"]
