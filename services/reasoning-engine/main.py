"""KAgent Reasoning Engine — entry point for Docker."""

import uvicorn

if __name__ == "__main__":
    uvicorn.run(
        "src.server:app",
        host="0.0.0.0",
        port=8200,
        log_level="info",
    )
