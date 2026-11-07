import os
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from finpay.backend.app.core.config import settings
from finpay.backend.app.core.init_db import init_db
from finpay.backend.app.routers import (
    auth,
    wallet,
    payment,
    merchant,
    reconciliation,
    websocket
)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialize DB schema and seed demo records
    init_db()
    yield

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description="Campus digital wallet and payment system with real-time cashback calculation, tier multipliers, idempotency, and reconciliation.",
    lifespan=lifespan
)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount API Routers
app.include_router(auth.router, prefix=settings.API_PREFIX)
app.include_router(wallet.router, prefix=settings.API_PREFIX)
app.include_router(payment.router, prefix=settings.API_PREFIX)
app.include_router(merchant.router, prefix=settings.API_PREFIX)
app.include_router(reconciliation.router, prefix=settings.API_PREFIX)
app.include_router(websocket.router)

@app.get(f"{settings.API_PREFIX}/health", tags=["Health"])
def health_check():
    return {
        "status": "healthy",
        "service": "FinPay Payment Core",
        "version": settings.VERSION,
        "currency_base": "paise (integer)",
        "talenthub_jwt_compatible": True
    }

# Frontend static serving
FRONTEND_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "frontend")
if os.path.exists(FRONTEND_DIR):
    app.mount("/static", StaticFiles(directory=FRONTEND_DIR), name="static")

    @app.get("/", include_in_schema=False)
    def serve_frontend_root():
        index_path = os.path.join(FRONTEND_DIR, "index.html")
        if os.path.exists(index_path):
            return FileResponse(index_path)
        return {"message": "FinPay API is running. Frontend index.html not yet found."}
