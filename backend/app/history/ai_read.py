"""Gemini reads the notes; Python checks every reading before the history check uses it.

    read_note(note)          NoteFacts for one note (pure: no network). Uses the note's saved
                             Gemini reading when there is one, otherwise the rules alone.
    ensure_read(notes, ...)  Ask Gemini to read notes that don't have a reading yet, save each
                             reading with the note (and in a local cache), and return counts.
    validate(reading, text)  Keep only what holds up against the note itself.

How a saved reading is used:
* The rules (extract.py) still run, on the English translation when the note isn't English.
  Their signals always count, and they decide what's ruled out ("denies pain").
* Gemini's observations add what the rules missed, but only when the quoted words really
  are in the note (or its translation) and the category is one Hunch knows.
* Serious events Gemini reports (a fall, chest pain, ...) count as urgent, again only with a
  verified quote that isn't itself a denial ("no falls").
* A note with no reading that the rules can't read either, and that doesn't look like
  English, is marked unreadable so the nurse is asked to read it (never silently "quiet").
"""

from __future__ import annotations

import hashlib
import json
import logging
import re
import threading
import unicodedata
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from difflib import SequenceMatcher
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

from ..models import note_reader
from .extract import COMPARATIVE, NEGATION, Meal, NoteFacts, Signal, _dedupe, extract

log = logging.getLogger(__name__)

VERSION = 1  # bump when the prompt or the checks change, so notes are read again
BATCH = 12   # notes per Gemini request
WORKERS = 4  # requests in flight at once

CATEGORIES = {"nutrition", "fluids", "energy", "mobility", "confusion", "pain",
              "sleep", "social", "toileting", "breathing"}
# Serious events -> (category, urgent). Same list the rules treat as urgent.
EVENTS = {"fall": "mobility", "chest_pain": "pain", "breathing_difficulty": "breathing",
          "hospital_transfer": "event", "unresponsive": "event", "seizure": "event", "bleeding": "event"}
QUOTE_MATCH = 0.85  # share of a quote that must appear in the note, allowing small slips

CACHE_FILE = Path(__file__).resolve().parents[2] / ".cache" / "note_readings.json"
_cache_lock = threading.Lock()
_cache: Optional[Dict[str, Dict[str, Any]]] = None


# ---------------------------------------------------------------------------
# Checking a reading against the note
# ---------------------------------------------------------------------------
def _norm(text: str) -> str:
    t = unicodedata.normalize("NFKC", text or "").casefold()
    t = re.sub(r"[^\w\s%]", " ", t)  # keep letters/digits in any script, drop punctuation
    return re.sub(r"\s+", " ", t).strip()


def quote_found(quote: str, *texts: Optional[str]) -> bool:
    """Is ``quote`` (nearly) word for word in one of ``texts``?"""
    q = _norm(quote)
    if len(q) < 2:
        return False
    for text in texts:
        t = _norm(text or "")
        if not t:
            continue
        if q in t:
            return True
        m = SequenceMatcher(None, q, t, autojunk=False).find_longest_match(0, len(q), 0, len(t))
        if m.size >= QUOTE_MATCH * len(q):
            return True
    return False


def validate(raw: Optional[Dict[str, Any]], text: str, model: Optional[str] = None) -> Dict[str, Any]:
    """Turn Gemini's raw reading into a saved reading, keeping only what holds up."""
    base = {"v": VERSION, "model": model, "read_at": datetime.now(timezone.utc).isoformat()}
    if not raw:
        return {**base, "status": "failed", "error": "Gemini returned no reading for this note."}
    lang = str(raw.get("language") or "en").strip().lower() or "en"
    translation = (raw.get("translation_en") or "").strip() or None
    if lang.split("-")[0] == "en":
        translation = None
    elif not translation:  # without it the rules can't read the note: try again later
        return {**base, "status": "failed", "error": f"No English translation for a note in '{lang}'."}
    kept: List[Dict[str, Any]] = []
    events: List[Dict[str, Any]] = []
    dropped: List[str] = []
    seen = set()
    for o in raw.get("observations") or []:
        cat, quote = o.get("category"), (o.get("source_text") or "").strip()
        sub, change = o.get("subcategory"), o.get("change")
        if cat not in CATEGORIES or o.get("direction") not in ("worsening", "improving"):
            dropped.append(f"{cat}: unknown category or direction")
            continue
        if cat == "toileting":
            if sub not in ("urine", "bowel") or change not in ("increased", "decreased"):
                dropped.append("toileting: missing urine/bowel or increased/decreased")
                continue
        else:
            sub = change = None
        if not quote_found(quote, text, translation):
            dropped.append(f"{cat}: quote not found in the note")
            continue
        key = (cat, sub, change)
        if key in seen:
            continue
        seen.add(key)
        kept.append({"category": cat, "subcategory": sub, "change": change, "direction": o["direction"],
                     "source_text": quote, "note": (o.get("note") or "").strip()[:200]})
    for e in raw.get("events") or []:
        etype, quote = e.get("type"), (e.get("source_text") or "").strip()
        if etype not in EVENTS:
            dropped.append(f"{etype}: unknown event")
        elif not quote_found(quote, text, translation):
            dropped.append(f"{etype}: quote not found in the note")
        elif _denies(quote):
            dropped.append(f"{etype}: the quote rules it out")
        else:
            events.append({"type": etype, "source_text": quote})
    return {**base, "status": "ok", "language": lang, "translation_en": translation,
            "observations": kept, "events": events, "dropped": dropped}


def _denies(quote: str) -> bool:
    """"No falls", "denies chest pain", "she did not fall": a denial in the first few words.
    (A denial later on, as in "found on the floor, did not hit her head", doesn't undo the event.)"""
    head = " ".join(re.findall(r"[\w']+", quote.lower())[:4])
    return bool(NEGATION.search(head))


def current(reading: Any) -> bool:
    return isinstance(reading, dict) and reading.get("v") == VERSION and reading.get("status") == "ok"


# ---------------------------------------------------------------------------
# One note -> NoteFacts
# ---------------------------------------------------------------------------
_EN_WORDS = set("""a an the and or but of to in on at for with from by was were is are be been had has have
he she her his him they them it this that today tonight morning afternoon evening night yesterday
ate eat eaten eating drank drink drinking breakfast lunch dinner meal meals snack fluids water juice tea
slept sleep sleepy tired walked walking up out bed room chair very more less than usual all most half
some few not no did does said says resident staff family care help needed bm voided pain""".split())


def looks_english(text: str) -> bool:
    """Rough check, used only for notes the rules found nothing in and Gemini hasn't read."""
    letters = [c for c in text if c.isalpha()]
    if not letters:
        return True
    if sum(1 for c in letters if ord(c) > 0x024F) > 0.3 * len(letters):  # mostly non-Latin script
        return False
    words = re.findall(r"[a-z']+", text.lower())
    if len(words) < 3:
        return True
    return sum(1 for w in words if w in _EN_WORDS) / len(words) >= 0.15


def read_note(note: Dict[str, Any]) -> NoteFacts:
    reading = note.get("ai_reading")
    text = note.get("note_text") or ""
    if not current(reading):
        facts = extract(note)
        if not (facts.signals or facts.meals or facts.negated) and not looks_english(text):
            facts.unreadable = True
        return facts

    translation = reading.get("translation_en")
    if translation:
        facts = extract({**note, "note_text": translation})
        facts.note = note
        facts.translation = translation
    else:
        facts = extract(note)
    facts.language = reading.get("language") or "en"
    facts.read_by = "ai"

    ruled_out = {s.match_key for s in facts.negated}
    extra: List[Signal] = []
    for o in reading.get("observations") or []:
        if o.get("direction") != "worsening":
            continue
        quote = o["source_text"]
        if o["category"] == "nutrition":
            if not facts.meals:  # the rules didn't find a meal amount in this note
                facts.meals.append(Meal(pct=None, phrase=quote, said_less=True, source="ai"))
            continue
        sig = Signal(category=o["category"], subcategory=o.get("subcategory"), change=o.get("change"),
                     phrase=quote, comparative=bool(COMPARATIVE.search(quote)), source="ai")
        if sig.match_key not in ruled_out:
            extra.append(sig)
    for e in reading.get("events") or []:
        extra.append(Signal(category=EVENTS[e["type"]], phrase=e["source_text"], urgent=True, source="ai"))
    facts.signals = _dedupe(facts.signals + extra)  # rules first: a rule's signal wins a tie
    return facts


# ---------------------------------------------------------------------------
# Asking Gemini, saving the readings
# ---------------------------------------------------------------------------
def _key(text: str) -> str:
    return hashlib.sha256(f"v{VERSION}\n{text}".encode()).hexdigest()


def _load_cache() -> Dict[str, Dict[str, Any]]:
    global _cache
    if _cache is None:
        try:
            _cache = json.loads(CACHE_FILE.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            _cache = {}
    return _cache


def _save_cache() -> None:
    try:
        CACHE_FILE.parent.mkdir(parents=True, exist_ok=True)
        tmp = CACHE_FILE.with_suffix(".tmp")
        tmp.write_text(json.dumps(_cache, ensure_ascii=False), encoding="utf-8")
        tmp.replace(CACHE_FILE)
    except OSError:  # read-only disk (e.g. Vercel): the database copy is enough
        pass


def ensure_read(notes: Iterable[Dict[str, Any]], store: Any = None, force: bool = False,
                progress: Any = None) -> Dict[str, int]:
    """Have Gemini read every note in ``notes`` that has no current reading.

    Each reading is put on the note dict, saved with the note (``store.save_note_reading``)
    and cached locally by note text, so the same note is never sent twice.
    """
    notes = [n for n in notes if n.get("note_text")]
    todo = notes if force else [n for n in notes if not current(n.get("ai_reading"))]
    out = {"notes": len(notes), "already_read": len(notes) - len(todo), "read": 0, "from_cache": 0, "failed": 0}
    count_lock = threading.Lock()
    if not todo:
        return out
    if not note_reader.ai_enabled():
        out["skipped"] = len(todo)
        return out

    def keep(note: Dict[str, Any], reading: Dict[str, Any]) -> None:
        note["ai_reading"] = reading
        if store is not None and note.get("id"):
            try:
                store.save_note_reading(note["id"], reading)
            except Exception:  # noqa: BLE001 - the reading still helps this run
                log.exception("Could not save the reading for note %s", note.get("id"))

    with _cache_lock:
        cache = _load_cache()
        hits = [] if force else [n for n in todo if current(cache.get(_key(n["note_text"])))]
    for n in hits:
        keep(n, cache[_key(n["note_text"])])
    out["from_cache"] = len(hits)
    hit_ids = {id(n) for n in hits}
    todo = [n for n in todo if id(n) not in hit_ids]

    def run_batch(batch: List[Dict[str, Any]]) -> None:
        try:
            result = note_reader.read_notes([n["note_text"] for n in batch])
        except Exception as e:  # noqa: BLE001 - leave these notes to the rules for now
            log.warning("Gemini note reading failed for %d note(s): %s", len(batch), e)
            with count_lock:
                out["failed"] += len(batch)
            return
        for n, raw in zip(batch, result["readings"]):
            reading = validate(raw, n["note_text"], result["model"])
            if reading["status"] != "ok":
                with count_lock:
                    out["failed"] += 1
                continue
            keep(n, reading)
            with _cache_lock:
                _load_cache()[_key(n["note_text"])] = reading
            with count_lock:
                out["read"] += 1
        if progress:
            with count_lock:
                progress(dict(out))

    batches = [todo[i:i + BATCH] for i in range(0, len(todo), BATCH)]
    with ThreadPoolExecutor(max_workers=WORKERS) as pool:
        list(pool.map(run_batch, batches))
    with _cache_lock:
        _save_cache()
    return out


def coverage(notes: Iterable[Dict[str, Any]]) -> Dict[str, Any]:
    notes = list(notes)
    return {"enabled": note_reader.ai_enabled(), "model": note_reader.models()[0],
            "notes": len(notes), "read_by_ai": sum(1 for n in notes if current(n.get("ai_reading")))}
