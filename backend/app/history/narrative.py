"""Plain-language summary for an alert, built only from evidence the history check found.

Uses app/explanation.py (prompt, validator, template fallback). With GEMINI_API_KEY
set, Gemini writes the summary and every claim is checked against the evidence IDs
and numbers it was given; an answer that fails the check twice falls back to the
template. Without a key, the template is used. Set HUNCH_LLM_EXPLAIN=0 to never call Gemini.
"""

from __future__ import annotations

import json
import logging
import os
import uuid
from typing import Any, Callable, Dict, List, Optional

from .. import explanation
from .check import LABELS, HistoryCheck

log = logging.getLogger(__name__)

_OBS_NS = uuid.UUID("6f1c3a52-6a2b-4c55-9d43-1f0d8f0c2b7e")  # fixed namespace for stable observation ids


def observation_id(note_id: str, match_key: str) -> str:
    """Same note + same signal -> same observation id, so re-runs don't duplicate rows."""
    return str(uuid.uuid5(_OBS_NS, f"{note_id}|{match_key}"))


def llm_enabled() -> bool:
    return (os.getenv("HUNCH_LLM_EXPLAIN", "1") != "0"
            and bool(os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")))


def _gemini() -> Optional[Callable[[str, str], Dict[str, Any]]]:
    if not llm_enabled():
        return None
    try:
        from google.genai import types

        from ..models.parser import MODEL, _client
    except ImportError:
        log.warning("google-genai is not installed; using template explanations.")
        return None

    def call(system: str, user: str) -> Dict[str, Any]:
        resp = _client().models.generate_content(
            model=MODEL, contents=user,
            config=types.GenerateContentConfig(system_instruction=system,
                                               response_mime_type="application/json"))
        return json.loads(resp.text)
    return call


def explain_check(c: HistoryCheck, observations: List[Dict[str, Any]]) -> Dict[str, Any]:
    findings = []
    for f in c.findings:
        if not (f.persisting or f.urgent):
            continue
        ids = list(dict.fromkeys(observation_id(ev.note_id, f.match_key) for ev in f.evidence if ev.note_id))
        if not ids:
            continue
        times = sorted(ev.recorded_at for ev in f.evidence)
        findings.append({"factor": LABELS.get(f.key, f.key).lower(), "message": f.reason.rstrip("."),
                         "evidence": ids, "first_seen": times[0], "last_seen": times[-1]})
    if not findings:
        return {"summary": c.title, "claims": [], "uncertainties": [], "source": "none"}

    alert = {"type": "urgent" if c.urgent else "combined", "findings": findings,
             "duration_days": c.duration_days}
    try:
        answer, source = explanation.explain(alert, {}, observations, [], llm=_gemini())
    except Exception:  # noqa: BLE001 - never let the summary break an alert
        log.exception("Explanation failed; using the template.")
        llm_input, _ = explanation.build_llm_input(alert, {}, observations, [])
        answer, source = explanation.template_explanation(llm_input), "template"
    if c.urgent:
        answer.setdefault("uncertainties", []).insert(
            0, "Urgent finding: follow the home's escalation procedure now; don't wait for more notes.")
    return {**answer, "source": source}
