"""Case-library vocabulary for generate_seed.py.

The 70 fictional historical cases are hand-written and live in cases.json (the
source of truth); this module loads them and defines the signal vocabulary that
generate_seed.check() validates them against.
"""
import json
from pathlib import Path

CATEGORIES = ["nutrition", "fluids", "energy", "mobility", "toileting", "pain", "confusion", "social", "sleep"]
SUBCATEGORIES = {"toileting": ("urine", "bowel")}  # categories that need a subcategory + change
CHANGES = ("increased", "decreased")

CASES = json.loads((Path(__file__).with_name("cases.json")).read_text(encoding="utf-8"))


def signal_key(o):
    """'nutrition', or 'toileting.bowel' for categories with a subcategory."""
    return f"{o['category']}.{o['subcategory']}" if o.get("subcategory") else o["category"]
