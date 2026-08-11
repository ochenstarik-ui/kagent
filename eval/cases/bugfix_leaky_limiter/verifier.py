import importlib.util
import pathlib
import sys

root = pathlib.Path(sys.argv[1])
spec = importlib.util.spec_from_file_location("candidate_limiter", root / "limiter.py")
assert spec and spec.loader
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
limiter = module.RateLimiter(limit=2)
assert [limiter.allow("alpha") for _ in range(3)] == [True, True, False]
independent = module.RateLimiter(limit=1)
assert independent.allow("alpha") is True
assert independent.allow("beta") is True
