"""Vercel entrypoint: the Hunch FastAPI app (backend/app/main.py).

Vercel runs this as one function. The same app serves the API under /api and the built
web app (frontend/dist, made by the build command in vercel.json), so sign-in cookies and
/api calls work exactly as they do locally. Local development still uses `python run.py`.
"""
import sys
from pathlib import Path

BACKEND = Path(__file__).resolve().parent / "backend"
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))  # the backend imports itself as `app.*`

from app import main as _main  # noqa: E402

app = _main.app
