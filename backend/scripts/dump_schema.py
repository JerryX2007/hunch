"""Save the Supabase table layout (names, columns, types) to backend/schema_snapshot.json.

Run from backend/:  python -m scripts.dump_schema
No row data and no keys are written, so the file is safe to commit.
"""

import json
import os

import httpx

from app import database as db

key = os.getenv("SUPABASE_SERVICE_ROLE_KEY") or os.getenv("SUPABASE_ANON_KEY") or ""
headers = {"apikey": key}
if key.startswith("eyJ"):
    headers["Authorization"] = f"Bearer {key}"

spec = httpx.get(f"{db.SUPABASE_URL}/rest/v1/", headers=headers, timeout=20).json()
if "definitions" not in spec:
    raise SystemExit(f"Could not read the schema: {str(spec)[:200]}")

out = {}
for table, d in sorted(spec["definitions"].items()):
    required = set(d.get("required", []))
    out[table] = {
        col: {
            "type": p.get("format") or p.get("type"),
            "required": col in required,
            "note": (p.get("description") or "").replace("\n", " ")[:160],
        }
        for col, p in d.get("properties", {}).items()
    }

path = db.BACKEND_DIR / "schema_snapshot.json"
path.write_text(json.dumps(out, indent=2) + "\n")
print(f"Wrote {path} ({len(out)} tables/views)")
for t, cols in out.items():
    print(f"  {t}: {', '.join(cols)}")
