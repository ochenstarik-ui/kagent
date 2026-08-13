"""Regression contract for Gateway connection metadata wiring."""

from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
GATEWAY_SOURCE = ROOT / "services" / "gateway" / "src" / "main.rs"


def test_gateway_server_supplies_connect_info_required_by_rate_limiter() -> None:
    source = GATEWAY_SOURCE.read_text(encoding="utf-8")

    assert "ConnectInfo(addr): ConnectInfo<SocketAddr>" in source
    assert "app.into_make_service_with_connect_info::<SocketAddr>()" in source
