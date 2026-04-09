"""
app/main.py - FastAPI application entry point.

Start with:
    uvicorn app.main:app --reload

Or run directly:
    python -m app.main
"""

import sys
import io
import os
import json
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.openapi.docs import get_swagger_ui_html

from app.core.config import settings
from app.core.logger import logger
from app.api.routes import router
from app.services.watcher_service import start_watcher

# Fix Windows console encoding
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")


@asynccontextmanager
async def lifespan(application: FastAPI):
    """Startup / shutdown lifecycle hooks."""
    logger.info("=" * 60)
    logger.info("API Doc Generator starting up")
    logger.info("Ollama: %s (model: %s)", settings.ollama_url, settings.ollama_model)
    logger.info("Spec:   %s", os.path.abspath(settings.spec_file))
    logger.info("SDK:    %s", os.path.abspath(settings.sdk_dir))
    logger.info("Watch:  %s", os.path.abspath(settings.sample_backend_dir))
    logger.info("=" * 60)

    # Create output directories
    os.makedirs(settings.spec_dir, exist_ok=True)
    os.makedirs(settings.sdk_dir, exist_ok=True)

    # Start file watcher in background
    observer = start_watcher()

    yield  # app is running

    # Shutdown
    logger.info("shutting down file watcher ...")
    observer.stop()
    observer.join(timeout=5)
    logger.info("shutdown complete")


app = FastAPI(
    title="API Documentation Generator",
    description="Generates OpenAPI specs and client SDKs from backend code using Ollama LLM",
    version="1.0.0",
    lifespan=lifespan,
    docs_url=None, # Define custom docs later
)

app.include_router(router)

# --- Frontend & UI Routes ---
frontend_dir = os.path.join(os.path.dirname(__file__), "frontend")
os.makedirs(frontend_dir, exist_ok=True)
app.mount("/static", StaticFiles(directory=frontend_dir), name="static")

@app.get("/", response_class=HTMLResponse, include_in_schema=False)
async def dashboard():
    """Serves the Premium visual Dashboard HTML."""
    index_path = os.path.join(frontend_dir, "index.html")
    if os.path.isfile(index_path):
        with open(index_path, "r", encoding="utf-8") as f:
            return HTMLResponse(content=f.read())
    return HTMLResponse(content="<h1>Dashboard missing</h1>")

@app.get("/generated-spec", include_in_schema=False)
async def get_generated_spec():
    """Serves the generated api.json directly to the dashboard."""
    if os.path.isfile(settings.spec_file):
        try:
            with open(settings.spec_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            return JSONResponse(content=data)
        except Exception:
            return JSONResponse(status_code=500, content={"error": "Failed to read spec"})
    return JSONResponse(status_code=404, content={"error": "Spec not found"})

@app.get("/docs", include_in_schema=False)
async def custom_swagger_ui_html():
    """Standard neat Swagger UI."""
    return get_swagger_ui_html(
        openapi_url=app.openapi_url,
        title=app.title + " - Swagger UI",
        oauth2_redirect_url=app.swagger_ui_oauth2_redirect_url,
    )


# Allow running directly: python -m app.main
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
