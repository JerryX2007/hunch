#!/usr/bin/env python3
"""Start all of Hunch with one command: API + analysis + nurse/PSW web app.

    python run.py              # Supabase if backend/.env is filled in, else built-in demo data
    python run.py --demo       # always use the in-memory demo data (no database or network needed)
    python run.py --seed       # first load test_data/ into Supabase (backend/scripts/seed_db.py)
    python run.py --build      # build the web app once and serve everything from one URL (:8000)
    python run.py --api-only   # just the API (docs at http://localhost:8000/docs)

What happens:
  1. uses backend/.venv (creating it and installing requirements.txt when anything is missing)
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
import secrets
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
# 1. Python with the backend's packages (creates backend/.venv and installs if needed)
# ---------------------------------------------------------------------------
# Import names of the packages the backend needs (google-genai only matters with a Gemini key,
# but it's in requirements.txt, so a missing one also triggers the install).
NEEDED = "import fastapi, uvicorn, pydantic_settings, dotenv, supabase, multipart, google.genai"
VENV = BACKEND / ".venv"
VENV_PY = VENV / ("Scripts/python.exe" if IS_WIN else "bin/python")


def _has_packages(py: str) -> bool:
    return subprocess.run([py, "-c", NEEDED], capture_output=True).returncode == 0


def ensure_python() -> str:
    if _has_packages(sys.executable):
        return sys.executable
    if not VENV_PY.exists():
        if sys.version_info < (3, 10):
            say(f"Python 3.10+ is needed (this is {sys.version.split()[0]}).")
            sys.exit(1)
        say("Creating backend/.venv (first run only)...")
        subprocess.run([sys.executable, "-m", "venv", str(VENV)], check=True)
    if not _has_packages(str(VENV_PY)):
        say("Installing backend packages into backend/.venv ...")
        r = subprocess.run([str(VENV_PY), "-m", "pip", "install", "-q", "-r", str(BACKEND / "requirements.txt")])
        if r.returncode != 0 or not _has_packages(str(VENV_PY)):
            say("Installing backend packages failed (see above). Try: "
                f"{VENV_PY.relative_to(ROOT)} -m pip install -r backend/requirements.txt")
            sys.exit(1)
    if Path(sys.executable).resolve() != VENV_PY.resolve():
        os.execv(str(VENV_PY), [str(VENV_PY), __file__, *sys.argv[1:]])
    return str(VENV_PY)


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------
def http(method: str, url: str, timeout: float = 60, headers: dict | None = None):
    req = urllib.request.Request(url, method=method, data=b"" if method == "POST" else None, headers=headers or {})
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
    """Install when node_modules is missing or any package in package.json isn't installed."""
    modules = FRONTEND / "node_modules"
    pkg = json.loads((FRONTEND / "package.json").read_text())
    wanted = {**pkg.get("dependencies", {}), **pkg.get("devDependencies", {})}
    missing = [name for name in wanted if not (modules / name / "package.json").exists()]
    if not modules.is_dir():
        say("Installing web app packages (first run only)...")
    elif missing:
        say(f"Installing new web app packages ({', '.join(missing)})...")
    else:
        return
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
    # Lets this script run the startup check without a nurse login; new each launch.
    env["HUNCH_INTERNAL_TOKEN"] = internal = secrets.token_urlsafe(32)
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
                s = http("POST", f"{api}/api/history/run", timeout=300, headers={"X-Hunch-Internal": internal})
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
        if health.get("mode") == "supabase":
            say("Nurses sign in with their own account (add one: cd backend && python -m scripts.create_nurse).")
        else:
            say("Demo nurse sign-in: nurse@demo.hunch / hunch-demo (or HUNCH_DEMO_EMAIL / HUNCH_DEMO_PASSWORD).")
        say("PSW note page (no sign-in): /psw   API docs: /docs on the API port.   Ctrl+C to stop.")
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
