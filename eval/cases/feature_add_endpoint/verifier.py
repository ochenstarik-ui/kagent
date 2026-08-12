import importlib.util
import pathlib
import sys

root = pathlib.Path(sys.argv[1])
spec = importlib.util.spec_from_file_location("candidate_app", root / "app.py")
assert spec and spec.loader
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
status, body = module.dispatch("GET", "/health/ready")
assert status == 200
assert body.get("status") == "ready"
assert type(body.get("uptime")) is int and body["uptime"] >= 0
assert module.dispatch("GET", "/health/live") == (200, {"status": "live"})
assert module.dispatch("POST", "/health/ready")[0] == 404
assert module.dispatch("GET", "/unknown")[0] == 404
assert (root / "tests" / "test_ready.py").is_file()
