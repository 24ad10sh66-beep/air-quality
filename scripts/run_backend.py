"""Start the local FastAPI backend."""

import uvicorn


if __name__ == "__main__":
    uvicorn.run(
        "air_quality.api.main:app",
        host="127.0.0.1",
        port=8000,
        reload=False,
    )
