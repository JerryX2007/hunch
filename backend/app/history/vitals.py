"""Vitals against published long-term-care limits and the resident's own usual.

    judge(measure, value, usual)  is this one reading out of line, and why?
    from_text(text)               vitals written in a note ("T 37.9, SpO2 88% RA, BP 100/60")
    merge_note_readings(...)      charted vitals plus ones only written in notes
(check.py turns out-of-line readings into findings.)

The limits come from the criteria nursing homes use for infection surveillance, adapted
so that a resident's own normal counts (a resident whose usual SpO2 is 91% is not flagged
for 91%). Numbers marked "proposed" are Hunch's own and NOT clinically validated.

* Temperature (IDSA, High et al. 2009): one reading above 37.8 C; or repeated readings above
  37.2 C; or a rise of more than 1.1 C over the resident's usual.
* Oxygen (McGeer): SpO2 below 94%, or more than 3 points below the resident's usual. For a
  resident whose usual is already below 94%, only the drop from their usual counts.
* Breathing rate (McGeer): 25 or more a minute.
* Pulse (Loeb minimum criteria): above 100.
* Blood pressure (proposed): systolic below 90, or 20 or more below the resident's usual.

A reading "counts" on its own when the source treats one reading as enough (fever above 37.8,
or 1.1 above usual; SpO2 below 90 or 5 below usual). Otherwise two out-of-line readings in
the recent window are needed, because nurses recheck a single odd value.
"""

from __future__ import annotations

import math
import re
import statistics
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

# key -> (reading field, label, unit, decimals)
MEASURES: Dict[str, Tuple[str, str, str, int]] = {
    "temperature": ("temp_c", "Temperature", " °C", 1),
    "oxygen": ("spo2", "Oxygen (SpO2)", "%", 0),
    "pulse": ("pulse", "Pulse", "/min", 0),
    "breathing_rate": ("resp_rate", "Breathing rate", "/min", 0),
    "blood_pressure": ("bp_systolic", "Blood pressure (systolic)", " mmHg", 0),
}
FIELDS = [m[0] for m in MEASURES.values()] + ["bp_diastolic"]
MIN_USUAL_READINGS = 3  # fewer earlier readings: no "usual" yet, standard limits only

# Red flags: serious on their own, don't wait for a pattern (proposed).
URGENT = {"temperature": 39.0, "oxygen_below": 88, "breathing_rate": 30, "pulse": 130, "systolic_below": 80}


@dataclass
class Judgement:
    out_of_line: bool
    alone: bool = False   # one reading is enough
    urgent: bool = False
    why: str = ""


def usual(readings: List[Dict[str, Any]], field: str) -> Optional[float]:
    """Median of earlier readings, rounded half up to the measure's precision (96.5 -> 97, so every
    screen shows the same number). None with fewer than MIN_USUAL_READINGS readings."""
    vals = [float(r[field]) for r in readings if r.get(field) is not None]
    if len(vals) < MIN_USUAL_READINGS:
        return None
    dec = next((m[3] for m in MEASURES.values() if m[0] == field), 1)
    return math.floor(statistics.median(vals) * 10 ** dec + 0.5) / 10 ** dec


def judge(key: str, value: float, usual_value: Optional[float]) -> Judgement:
    u = usual_value
    if key == "temperature":
        urgent = value >= URGENT["temperature"]
        if value > 37.8:
            return Judgement(True, True, urgent, "above 37.8 °C, a fever by the IDSA definition")
        rise = round(value - u, 1) if u is not None else None  # 37.6 - 36.5 is 1.1000000000000014
        if rise is not None and rise > 1.1:
            return Judgement(True, True, urgent, f"{rise:.1f} °C above usual: a rise of more than 1.1 °C counts as fever (IDSA)")
        if value > 37.2:
            return Judgement(True, False, urgent, "above 37.2 °C: a fever when repeated (IDSA)")
        return Judgement(False)
    if key == "oxygen":
        drop = round(u - value, 1) if u is not None else 0
        urgent = value < URGENT["oxygen_below"] or (value < 90 and drop > 3)
        alone = value < 90 or drop >= 5
        if u is not None and drop > 3:
            return Judgement(True, alone, urgent, f"{drop:.0f} points below usual (McGeer: a drop of more than 3)")
        if value < 94 and (u is None or u >= 94):
            return Judgement(True, alone, urgent, "below 94% (McGeer)")
        return Judgement(False)
    if key == "breathing_rate":
        if value >= 25:
            return Judgement(True, False, value >= URGENT["breathing_rate"], "25 or more a minute (McGeer)")
        return Judgement(False)
    if key == "pulse":
        if value > 100:
            return Judgement(True, False, value >= URGENT["pulse"], "above 100 (Loeb)")
        return Judgement(False)
    if key == "blood_pressure":
        urgent = value < URGENT["systolic_below"]
        if value < 90:
            return Judgement(True, False, urgent, "systolic below 90 (proposed)")
        if u is not None and round(u - value, 1) >= 20:
            return Judgement(True, False, urgent, f"{u - value:.0f} below usual (proposed: 20 or more)")
        return Judgement(False)
    raise KeyError(key)


def fmt(key: str, value: Optional[float]) -> str:
    if value is None:
        return "—"
    _, _, unit, dec = MEASURES[key]
    return f"{value:.{dec}f}{unit}"


def flags(reading: Dict[str, Any], usuals: Dict[str, Optional[float]]) -> Dict[str, str]:
    """{field: why} for each out-of-line value in one reading (for the vitals table)."""
    out = {}
    for key, (field, *_rest) in MEASURES.items():
        v = reading.get(field)
        if v is not None:
            j = judge(key, float(v), usuals.get(key))
            if j.out_of_line:
                out[field] = j.why
    return out


# ---------------------------------------------------------------------------
# Vitals written in notes
# ---------------------------------------------------------------------------
_R = re.IGNORECASE
TEXT_PATTERNS = {
    "temp_c": re.compile(r"\b(?:temp(?:erature)?|t)\s*[:=]?\s*(3[4-9](?:\.\d)?|4[0-2](?:\.\d)?)\s*(?:°\s*c|c\b)?", _R),
    "spo2": re.compile(r"\b(?:spo2|o2 sats?|sats?|o2)\s*[:=]?\s*(\d{2,3})\s*%", _R),
    "pulse": re.compile(r"\b(?:hr|pulse|p)\s*[:=]?\s*(\d{2,3})\b(?!\s*%)", _R),
    "resp_rate": re.compile(r"\b(?:rr|resp(?:irations?)?)\s*[:=]?\s*(\d{1,2})\b", _R),
    "bp": re.compile(r"\bbp\s*[:=]?\s*(\d{2,3})\s*/\s*(\d{2,3})", _R),
}
RANGES = {"temp_c": (30, 43), "spo2": (50, 100), "pulse": (25, 220), "resp_rate": (4, 60),
          "bp_systolic": (50, 260), "bp_diastolic": (20, 160)}


def from_text(text: str) -> List[Dict[str, Any]]:
    """Readings written in a note, in order. "T 37.6 ... rechecked 1h later T 36.7" gives two."""
    found: List[Tuple[int, str, float]] = []
    for field, rx in TEXT_PATTERNS.items():
        for m in rx.finditer(text or ""):
            if field == "bp":
                found += [(m.start(), "bp_systolic", float(m.group(1))), (m.start(), "bp_diastolic", float(m.group(2)))]
            else:
                found.append((m.start(), field, float(m.group(1))))
    readings: List[Dict[str, Any]] = []
    cur: Dict[str, Any] = {}
    for _, field, value in sorted(found):
        lo, hi = RANGES[field]
        if not lo <= value <= hi:
            continue
        if field in cur:  # the same measure again: a second reading
            readings.append(cur)
            cur = {}
        cur[field] = value
    if cur:
        readings.append(cur)
    return readings


def _time(r: Dict[str, Any]) -> datetime:
    v = r["recorded_at"]
    return v if isinstance(v, datetime) else datetime.fromisoformat(str(v).replace("Z", "+00:00")).replace(tzinfo=None)


def merge_note_readings(entered: List[Dict[str, Any]], notes: List[Dict[str, Any]],
                        texts: Dict[str, str]) -> List[Dict[str, Any]]:
    """Vitals charted in the vitals table, plus ones only written in notes. A note's value is
    dropped when the same measure was charted within 2 hours (the same reading, written twice)."""
    out = list(entered)
    for n in notes:
        text = texts.get(n.get("id") or "", n.get("note_text") or "")
        for r in from_text(text):
            when = _time(n)
            keep = {f: v for f, v in r.items()
                    if not any(e.get(f) is not None and abs((_time(e) - when).total_seconds()) <= 7200 for e in entered)}
            if keep:
                out.append({**{f: None for f in FIELDS}, **keep, "id": None, "note_id": n.get("id"),
                            "resident_id": n.get("resident_id"), "recorded_at": n["recorded_at"],
                            "author_role": n.get("author_role"), "author_name": n.get("author_name"), "source": "note"})
    return out
