.PHONY: bootstrap infra-up infra-down check test

bootstrap:
	cp -n .env.example .env || true
	pnpm install

infra-up:
	docker compose up -d

infra-down:
	docker compose down

check:
	pnpm check
	pnpm rust:check

test:
	pnpm test
	cargo test --manifest-path services/gateway/Cargo.toml
