#!/usr/bin/env python3
"""Start all of Hunch with one command: API + analysis + nurse/PSW web app.

    python run.py              # Supabase if backend/.env is filled in, else built-in demo data
    python run.py --demo       # always use the in-memory demo data (no database or network needed)
    python run.py --seed       # first load test_data/ into Supabase (backend/scripts/seed_db.py)
    python run.py --build      # build the web app once and serve everything from one URL (:8000)
    python run.py --api-only   # just the API (docs at http://localhost:8000/docs)

What happens:
  1. finds a Python with the backend's packages (backend/.venv is used automatically)
  2. (--seed) loads test_data/ into Supabase
  3. starts the FastAPI backend on :8000
  4. runs the history check for every resident and saves alerts + similar cases
  5. starts the web app (Vite on :5173, installing npm packages the first time)
Ctrl+C stops everything.
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import signal
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent
BACKEND = ROOT / "backend"
FRONTEND = ROOT / "frontend"
IS_WIN = os.name == "nt"


def say(msg: str) -> None:
    print(f"[hunch] {msg}", flush=True)


# ---------------------------------------------------------------------------
# 1. Python with the backend's packages
# ---------------------------------------------------------------------------
def _has_backend_packages() -> bool:
    try:
        import dotenv, fastapi, pydantic_settings, uvicorn  # noqa: F401,E401
        return True
    except ImportError:
        return False


def ensure_python() -> str:
    if _has_backend_packages():
        return sys.executable
    venv_py = BACKEND / ".venv" / ("Scripts/python.exe" if IS_WIN else "bin/python")
    if venv_py.exists() and Path(sys.executable).resolve() != venv_py.resolve():
        say(f"Using {venv_py.relative_to(ROOT)}")
        os.execv(str(venv_py), [str(venv_py), __file__, *sys.argv[1:]])
    activate = r".venv\Scripts\activate" if IS_WIN else "source .venv/bin/activate"
    say("The backend's Python packages aren't installed. Run once:")
    print(f"    cd backend && {Path(sys.executable).name} -m venv .venv && {activate} && "
          "pip install -r requirements.txt\n  then: python run.py")
    sys.exit(1)


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------
def http(method: str, url: str, timeout: float = 60):
    req = urllib.request.Request(url, method=method, data=b"" if method == "POST" else None)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode())


def start(cmd: list[str], cwd: Path, env: dict) -> subprocess.Popen:
    # Own process group, so Ctrl+C / shutdown also stops children (uvicorn reloader, vite).
    kw = {"creationflags": subprocess.CREATE_NEW_PROCESS_GROUP} if IS_WIN else {"start_new_session": True}
    return subprocess.Popen(cmd, cwd=cwd, env=env, **kw)


def stop(p: subprocess.Popen) -> None:
    if p.poll() is not None:
        return
    try:
        if IS_WIN:
            p.terminate()
        else:
            os.killpg(p.pid, signal.SIGTERM)
        p.wait(timeout=8)
    except Exception:  # noqa: BLE001
        p.kill()


def npm() -> str | None:
    return shutil.which("npm.cmd" if IS_WIN else "npm") or shutil.which("npm")


def npm_install_if_needed(npm_cmd: str, env: dict) -> None:
    if not (FRONTEND / "node_modules").is_dir():
        say("Installing web app packages (first run only)...")
        subprocess.run([npm_cmd, "install", "--no-audit", "--no-fund"], cwd=FRONTEND, env=env, check=True)


# ---------------------------------------------------------------------------
def main() -> int:
    ap = argparse.ArgumentParser(description="Run Hunch (API + analysis + web app).")
    ap.add_argument("--demo", action="store_true", help="use in-memory demo data instead of Supabase")
    ap.add_argument("--seed", action="store_true", help="load test_data/ into Supabase before starting")
    ap.add_argument("--build", action="store_true", help="build the web app and serve it from the API port")
    ap.add_argument("--api-only", action="store_true", help="don't start the web app")
    ap.add_argument("--no-analysis", action="store_true", help="don't run the history check at startup")
    ap.add_argument("--port", type=int, default=8000, help="API port (default 8000)")
    args = ap.parse_args()

    py = ensure_python()

    def _interrupt(*_):  # closing the terminal / `kill` stops the children too
        raise KeyboardInterrupt
    for sig in ("SIGTERM", "SIGHUP"):
        if hasattr(signal, sig):
            signal.signal(getattr(signal, sig), _interrupt)
    env = {**os.environ, "PYTHONUNBUFFERED": "1"}
    if args.demo:
        env["HUNCH_MODE"] = "demo"
    api = f"http://127.0.0.1:{args.port}"
    env["HUNCH_API"] = api
    procs: list[subprocess.Popen] = []

    try:
        # 2. seed
        if args.seed:
            if args.demo:
                say("--seed ignored: demo mode doesn't use the database.")
            else:
                say("Loading test_data/ into Supabase...")
                if subprocess.run([py, "-m", "scripts.seed_db"], cwd=BACKEND, env=env).returncode != 0:
                    say("Seeding failed (see above). Fix it, or run: python run.py --demo")
                    return 1

        # (--build) build before the API starts, so the API finds frontend/dist
        npm_cmd = npm()
        if args.build and not args.api_only:
            if not npm_cmd:
                say("npm not found; install Node.js 20+ to build the web app.")
                return 1
            npm_install_if_needed(npm_cmd, env)
            say("Building the web app...")
            subprocess.run([npm_cmd, "run", "build"], cwd=FRONTEND, env=env, check=True)

        # 3. backend
        say(f"Starting API on {api} ...")
        cmd = [py, "-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", str(args.port)]
        if not args.build:
            cmd.append("--reload")
        api_proc = start(cmd, BACKEND, env)
        procs.append(api_proc)

        health = None
        for _ in range(60):
            if api_proc.poll() is not None:
                say("The API stopped during startup (error above).")
                return 1
            try:
                health = http("GET", f"{api}/api/health", timeout=5)
                break
            except (urllib.error.URLError, ConnectionError, TimeoutError):
                time.sleep(0.5)
        if not health:
            say("The API didn't answer within 30 s.")
            return 1
        mode = "Supabase" if health.get("mode") == "supabase" else "demo data (in memory)"
        say(f"API up. Data: {mode}. Summaries: {'Gemini (checked)' if health.get('llm') else 'template'}.")
        if health.get("database") != "ok":
            say(f"Database problem: {health.get('database')}")
            say("Pages will show this error. To present without the database: python run.py --demo")

        # 4. analysis
        if not args.no_analysis and health.get("database") == "ok":
            say("Running the history check for every resident...")
            try:
                s = http("POST", f"{api}/api/history/run", timeout=300)
                for r in s["residents"]:
                    if r.get("alert_id"):
                        state = "dismissed earlier, nothing new" if r.get("suppressed") else r["title"]
                        say(f"  {r['resident_id']}: {r['tier'].upper()} - {state}")
                say(f"  {len(s['residents'])} residents checked, {s['alerts']} alert(s) saved.")
            except urllib.error.HTTPError as e:
                say(f"History check failed: {e.read().decode()[:300]}")

        # 5. web app
        url = f"http://localhost:{args.port}/nurse" if args.build else "http://localhost:5173/nurse"
        if not args.api_only and not args.build:
            if not npm_cmd:
                say("npm not found: install Node.js 20+ for the web app. The API is still running.")
                url = f"{api}/docs"
            else:
                npm_install_if_needed(npm_cmd, env)
                procs.append(start([npm_cmd, "run", "dev", "--", "--port", "5173", "--strictPort"], FRONTEND, env))
        elif args.api_only:
            url = f"{api}/docs"

        print()
        say(f"Ready: open {url}")
        say("PSW note page: /psw   API docs: /docs on the API port.   Ctrl+C to stop.")
        print()
        while all(p.poll() is None for p in procs):
            time.sleep(0.5)
        say("A process stopped; shutting down.")
        return 1
    except KeyboardInterrupt:
        print()
        say("Stopping...")
        return 0
    finally:
        for p in reversed(procs):
            stop(p)


if __name__ == "__main__":
    sys.exit(main())
