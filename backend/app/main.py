from __future__ import annotations

from fastapi import FastAPI

from backend.app.api.routes.health import router as health_router
from backend.app.api.routes.sku_comparison import router as sku_router

app = FastAPI(
    title="Tire Platform API",
    description="Backend API skeleton for AI Missing SKU Finder and future Tire/Wheel Commerce OS.",
    version="0.1.0",
)

app.include_router(health_router)
app.include_router(sku_router)
