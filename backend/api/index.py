"""Vercel serverless entrypoint.

Vercel runs the single ASGI app in this file for every route (see
``vercel.json`` rewrites). Using the same FastAPI app as local ``uvicorn`` means
the HTTP API, health check, and the cron ingestion trigger share one code path.
"""

from app.main import app  # noqa: F401