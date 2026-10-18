"""Gemini reads care notes: language, English translation, observations and serious events.

This is the language step only. Gemini says what a note *reports*, quoting the note's own
words; app/history/ai_read.py then checks every quote against the note before anything
is used, and the history check (Python) decides what it means for the resident.

    read_notes(["Ate half her lunch, very sleepy.", "Nahulog siya kaninang umaga."])

Several notes go in one request (one reading per note, matched by index). Needs
GEMINI_API_KEY; HUNCH_AI_READ=0 turns it off. GEMINI_NOTE_MODEL (or GEMINI_MODEL) picks
the model; if it fails, the fallback model is tried once.
"""

from __future__ import annotations

import json
import os
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, List, Literal, Optional

from dotenv import load_dotenv
from pydantic import BaseModel, ValidationError

load_dotenv(Path(__file__).resolve().parents[2] / ".env")

DEFAULT_MODEL = "gemini-3.5-flash-lite"
FALLBACK_MODEL = "gemini-3.1-flash-lite"
TIMEOUT_MS = 45_000

Category = Literal["nutrition", "fluids", "energy", "mobility", "confusion", "pain",
                   "sleep", "social", "toileting", "breathing"]
EventType = Literal["fall", "chest_pain", "breathing_difficulty", "hospital_transfer",
                    "unresponsive", "seizure", "bleeding"]


# The response schema Gemini fills in (no default values: the Gemini API's schema doesn't
# take them). Python checks every field afterwards (ai_read.validate) and drops what
# doesn't hold up, so an odd answer is read leniently rather than failing the batch.
class AIObservation(BaseModel):
    category: Category
    direction: Literal["worsening", "improving"]
    source_text: str
    note: str
    subcategory: Optional[Literal["urine", "bowel"]]
    change: Optional[Literal["increased", "decreased"]]


class AIEvent(BaseModel):
    type: EventType
    source_text: str


class AINoteReading(BaseModel):
    index: int
    language: str
    translation_en: Optional[str]
    observations: List[AIObservation]
    events: List[AIEvent]


class AIBatch(BaseModel):
    readings: List[AINoteReading]


SYSTEM_INSTRUCTION = """
You read care notes written by staff in a long-term care home and turn each one into
structured data. Report only what the note says. Never diagnose, guess causes or add details.

Input: a JSON list of notes, each {"index": n, "text": "..."}. Return exactly one reading
per note, with the same index.

For each note:
- language: the note's main language as a short code ("en", "tl", "pa", "zh", "yue", "hi", "es", "fr", ...).
- translation_en: if the note is not in English, a faithful, literal English translation that
  keeps every number, amount, time and name exactly. If the note is in English, null.
- observations: changes in the resident that the note reports, at most one per category:
  - nutrition: appetite, how much was eaten, eating difficulties
  - fluids: drinking and fluid intake
  - energy: tired, drowsy, hard to wake, lethargic
  - mobility: walking, transfers, balance, needing more help to move
  - confusion: disoriented, new or worse confusion, agitation, hallucinations
  - pain: pain, aches, discomfort, wincing, guarding
  - sleep: night-time sleep problems
  - social: withdrawn, declining visits or usual activities
  - toileting: changes in urine or bowel habits
  - breathing: cough, wheeze, noisy or fast breathing, short of breath
  For each one:
  - direction: "worsening" for a decline or new problem, "improving" for a recovery.
    Leave out anything the note rules out ("denies pain", "no cough") and anything the note
    describes as the resident's usual.
  - subcategory and change: toileting only. subcategory "urine" or "bowel"; change "increased"
    or "decreased" (how often or how much). Null for every other category.
  - source_text: the exact words from the note that support it, copied word for word in the
    note's own language. Do not translate, shorten or reword them.
  - note: a short, neutral English description.
- events: serious events the note says actually happened: fall (including being found on the
  floor), chest_pain, breathing_difficulty, hospital_transfer, unresponsive, seizure, bleeding.
  source_text: the exact words from the note, word for word. Leave out events that were ruled
  out or are only a risk ("at risk of falls", "no falls").
If nothing qualifies, return empty lists.
""".strip()


def ai_enabled() -> bool:
    return (os.getenv("HUNCH_AI_READ", "1") != "0"
            and bool(os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")))


def models() -> List[str]:
    primary = os.getenv("GEMINI_NOTE_MODEL") or os.getenv("GEMINI_MODEL") or DEFAULT_MODEL
    return [primary] + ([FALLBACK_MODEL] if primary != FALLBACK_MODEL else [])


@lru_cache(maxsize=1)
def _client():
    from google import genai
    from google.genai import types
    return genai.Client(http_options=types.HttpOptions(timeout=TIMEOUT_MS))


def _call(model: str, notes: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    from google.genai import types
    resp = _client().models.generate_content(
        model=model,
        contents=json.dumps(notes, ensure_ascii=False),
        config=types.GenerateContentConfig(
            system_instruction=SYSTEM_INSTRUCTION,
            response_mime_type="application/json",
            response_schema=AIBatch,
        ),
    )
    if isinstance(resp.parsed, AIBatch):
        return [r.model_dump() for r in resp.parsed.readings]
    try:
        return [r.model_dump() for r in AIBatch.model_validate_json(resp.text).readings]
    except ValidationError:  # not quite the schema: take the readings as plain JSON
        data = json.loads(resp.text)
        return [r for r in data.get("readings", []) if isinstance(r, dict) and isinstance(r.get("index"), int)]


def read_notes(texts: List[str]) -> Dict[str, Any]:
    """Read several notes in one request.

    Returns {"model": ..., "readings": [reading or None, ...]} in the same order as ``texts``
    (None when Gemini skipped a note). Raises when every model fails.
    """
    notes = [{"index": i, "text": t} for i, t in enumerate(texts)]
    last: Optional[Exception] = None
    for model in models():
        try:
            by_index = {r["index"]: r for r in _call(model, notes)}
            return {"model": model, "readings": [by_index.get(i) for i in range(len(texts))]}
        except Exception as e:  # noqa: BLE001 - try the fallback model, then give up
            last = e
    raise RuntimeError(f"Gemini could not read the notes: {type(last).__name__}: {last}") from last
