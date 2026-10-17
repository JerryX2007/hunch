from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .config import settings
from .routers import health, history, residents

app = FastAPI(title="Hunch API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Every endpoint lives under /api so the frontend can proxy (dev) or share an origin (prod).
app.include_router(health.router, prefix="/api")
app.include_router(residents.router, prefix="/api")
app.include_router(history.router, prefix="/api")
