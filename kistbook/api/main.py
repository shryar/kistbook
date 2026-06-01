from __future__ import annotations

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

app = FastAPI(title="KistBook Reminder Engine", version="0.1.0")


@app.exception_handler(Exception)
async def generic_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    return JSONResponse(
        status_code=500,
        content={"error": "internal_server_error", "detail": str(exc)},
    )


from kistbook.api.routes import admin, customers, logs, retailers, webhooks  # noqa: E402

app.include_router(retailers.router)
app.include_router(customers.router)
app.include_router(logs.router)
app.include_router(webhooks.router)
app.include_router(admin.router)

import os  # noqa: E402

_static_dir = os.path.join(os.path.dirname(__file__), "static")
if os.path.isdir(_static_dir):
    app.mount("/", StaticFiles(directory=_static_dir, html=True), name="static")
