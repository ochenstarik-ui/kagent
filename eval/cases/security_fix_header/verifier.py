import importlib.util
import pathlib
import sys

root = pathlib.Path(sys.argv[1])
spec = importlib.util.spec_from_file_location("candidate_web", root / "web.py")
assert spec and spec.loader
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
for path, expected_status in (("/", 200), ("/missing", 404)):
    status, _, headers = module.response(path)
    assert status == expected_status
    assert headers.get("X-Content-Type-Options") == "nosniff"
_, _, headers = module.response("/", {"X-Request-ID": "abc", "X-Content-Type-Options": "unsafe"})
assert headers.get("X-Request-ID") == "abc"
assert headers.get("X-Content-Type-Options") == "nosniff"
