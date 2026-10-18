"""Gemini-based extraction: free-text care note -> structured observations.

Run the checks from backend/:
    python -m app.models.test_parser        # one sample note
    python -m app.models.evaluate_parser    # 10 labelled notes

Needs GEMINI_API_KEY in backend/.env (see .env.example).
"""

import os
from functools import lru_cache
from pathlib import Path

from dotenv import load_dotenv
from google import genai
from google.genai import types

from .observation import ObservationResponse

# Load backend/.env no matter which directory the script is started from.
load_dotenv(Path(__file__).resolve().parents[2] / ".env")

MODEL = os.getenv("GEMINI_MODEL", "gemini-3.1-flash-lite")

SYSTEM_INSTRUCTION = """
You extract structured observations from free-text care notes about a care-home resident.

Extract only evidence-supported changes in these categories:
- nutrition: appetite, food intake, eating difficulties
- fluids: drinking and fluid intake
- energy: tiredness, drowsiness, difficulty waking, daytime lethargy
- mobility: walking, transfers, balance, falls, assistance needed
- confusion: disorientation, new confusion, repeated questions, difficulty recognising people
- pain: pain, aches, discomfort, wincing, guarding
- sleep: night-time sleep problems, waking, unusual sleep patterns
- social: withdrawal, declining visits or usual activities
- toileting: changes in urination or bowel habits

For each observation:
- `category`: Choose one category from the list.
- `direction`: Use "worsening" for a supported decline from usual, or "improving" for a supported recovery. Do not infer change without sufficient context. Omit observations whose direction is unclear.
- `subcategory`: For toileting, use "urine" or "bowel"; otherwise null.
- `change`: For toileting, use "increased" or "decreased" to describe the observed frequency or occurrence change; otherwise null. This describes what changed, not whether the resident is improving.
- `note`: Give a short, neutral description grounded in the input. Preserve relevant quantities and qualifiers.
- `event_date`: Use YYYY-MM-DD only when the date and year are known or unambiguously derivable; otherwise null. Never guess.
- `source_text`: Copy the exact supporting wording from the input.

Create separate observations for distinct applicable categories, but avoid duplicates. Do not infer causes or diagnoses, or invent details. If no observations qualify, return an empty observations list.
"""


@lru_cache(maxsize=1)
def _client() -> genai.Client:
    """Created on first use, so importing this module never needs an API key."""
    if not (os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")):
        raise RuntimeError("GEMINI_API_KEY is not set. Add it to backend/.env (see .env.example).")
    return genai.Client()


def extract(note_text: str) -> ObservationResponse:
    response = _client().models.generate_content(
        model=MODEL,
        contents=note_text,
        config=types.GenerateContentConfig(
            system_instruction=SYSTEM_INSTRUCTION,
            response_mime_type="application/json",
            response_schema=ObservationResponse,
            # No temperature=0: Google warns it can make Gemini 3 models loop.
        ),
    )

    if response.parsed is None:
        raise ValueError("Gemini did not return a valid structured response.")

    return response.parsed
