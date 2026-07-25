"""KAgent Reasoning Engine — entry point."""

import uvicorn

if __name__ == "__main__":
    uvicorn.run(
        "services.reasoning_engine.src.server:app",
        host="0.0.0.0",
        port=8200,
        reload=True,
        log_level="info",
    )
