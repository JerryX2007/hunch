import logging
import os
import threading
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from .config import settings
from .routers import auth, health, history, profile, residents

log = logging.getLogger("hunch")

def _catch_up_note_reading() -> None:
    """Have Gemini read notes that don't have a reading yet (run.py turns this on)."""
    from .history import service
    from .models.note_reader import ai_enabled
    if not ai_enabled():
        return
    try:
        counts = service.read_all_notes(progress=lambda c: log.info(
            "Gemini note reading: %d read, %d from cache, %d failed", c["read"], c["from_cache"], c["failed"]))
        log.info("Gemini note reading done: %s", counts)
    except Exception:  # noqa: BLE001 - the rules keep working without it
        log.exception("Gemini note reading catch-up failed; notes are read by the rules.")


@asynccontextmanager
async def lifespan(_app: FastAPI):
    if os.getenv("HUNCH_AI_BACKFILL") == "1":
        threading.Thread(target=_catch_up_note_reading, name="note-reading-catch-up", daemon=True).start()
    yield


app = FastAPI(title="Hunch API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(Exception)
async def unexpected_error(request: Request, exc: Exception) -> JSONResponse:
    """Send the reason to the browser as JSON (e.g. 'Supabase unreachable') instead of a bare 500."""
    log.exception("Unhandled error on %s", request.url.path)
    return JSONResponse(status_code=500, content={"detail": f"{type(exc).__name__}: {exc}"})


# Every endpoint lives under /api so the frontend can proxy (dev) or share an origin (prod).
app.include_router(health.router, prefix="/api")
app.include_router(residents.router, prefix="/api")
app.include_router(history.router, prefix="/api")
app.include_router(auth.router, prefix="/api")  # /api/auth/signin, /me, /logout
app.include_router(profile.router, prefix="/api")  # /api/profile/me

# Serve the built web app (frontend/dist, made by `python run.py --build`) from the same origin.
DIST = Path(__file__).resolve().parents[2] / "frontend" / "dist"
if (DIST / "index.html").is_file():
    if (DIST / "assets").is_dir():
        app.mount("/assets", StaticFiles(directory=DIST / "assets"), name="assets")

    @app.get("/{path:path}", include_in_schema=False)
    def spa(path: str) -> FileResponse:
        if path.startswith("api/"):
            raise HTTPException(status_code=404, detail="Not found")
        f = (DIST / path).resolve()
        if path and f.is_file() and DIST.resolve() in f.parents:
            return FileResponse(f)
        return FileResponse(DIST / "index.html")  # client-side routes like /nurse
