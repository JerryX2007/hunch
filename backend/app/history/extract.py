"""Turn free-text care notes into structured signals (the rules half of note reading).

Gemini's reading of a note is merged in by ai_read.py; this module is the part that
always works, with or without it.

Rule-based on purpose: every signal keeps the exact phrase it came from, so
the nurse can see *why* something was flagged, and the same note always gives
the same answer.

Vocabulary matches the historical case library (test_data/cases.json):
nutrition, fluids, energy, mobility, toileting (urine / bowel), pain,
confusion, social, sleep. Two extras that the library doesn't use:
breathing, and "event" (e.g. a hospital transfer) for urgent escalation.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional


@dataclass(frozen=True)
class Signal:
    category: str
    phrase: str                       # the words that triggered it
    subcategory: Optional[str] = None  # toileting only: urine / bowel
    change: Optional[str] = None       # toileting only: decreased / increased
    direction: str = "worsening"
    urgent: bool = False               # serious on its own, don't wait for a pattern
    comparative: bool = False          # note itself says "than usual", "unusual", ...
    stated_days: Optional[int] = None  # e.g. "No BM for 5 days"
    source: str = "rules"              # "rules", or "ai" when only Gemini's reading found it

    @property
    def key(self) -> str:
        """Category key used in alerts and eval files, e.g. 'toileting.bowel'."""
        return f"{self.category}.{self.subcategory}" if self.subcategory else self.category

    @property
    def match_key(self) -> str:
        """Key used for case matching; includes the direction of a toileting change."""
        return f"{self.key}.{self.change}" if self.change else self.key


@dataclass(frozen=True)
class Meal:
    pct: Optional[float]   # None when the note only says "less than usual"
    phrase: str
    said_less: bool = False
    source: str = "rules"


@dataclass
class NoteFacts:
    note: Dict[str, Any]
    time: datetime
    signals: List[Signal] = field(default_factory=list)
    negated: List[Signal] = field(default_factory=list)  # mentioned, but ruled out
    meals: List[Meal] = field(default_factory=list)
    read_by: str = "rules"              # "ai" when a checked Gemini reading was used (ai_read.py)
    language: Optional[str] = None      # from Gemini's reading
    translation: Optional[str] = None   # English translation, when the note isn't English
    unreadable: bool = False            # no reading, nothing the rules know, not English


# ---------------------------------------------------------------------------
# Patterns. Each rule: (category, regex, options)
#   neg=False   -> the phrase is itself a finding even though it contains "no"/"not"
#                  (e.g. "No BM for 4 days", "voided only once")
#   urgent=True -> escalate immediately
# ---------------------------------------------------------------------------
_R = re.IGNORECASE


def _rule(category, pattern, sub=None, change=None, neg=True, urgent=False, days_group=None):
    return dict(category=category, rx=re.compile(pattern, _R), sub=sub, change=change,
                neg=neg, urgent=urgent, days_group=days_group)


RULES = [
    # --- urgent events --------------------------------------------------------
    _rule("mobility", r"found on (?:the )?floor|\bfell\b|had a fall|unable to bear weight", urgent=True),
    _rule("pain", r"chest pain", urgent=True),
    _rule("breathing", r"short(?:ness)? of breath|difficulty breathing|labou?red breathing|gasping", urgent=True),
    _rule("event", r"transferred to (?:the )?hospital|sent to (?:the )?(?:er|hospital|emergency)|unresponsive|seizure|blood in (?:stool|urine)|vomiting blood", urgent=True),
    # --- fluids ---------------------------------------------------------------
    _rule("fluids", r"drinking less|drank less|drinking (?:very )?little|left most of (?:his|her) (?:juice|drink|fluids|water|tea)"
                    r"|poor fluid|refus\w* (?:fluids|drinks)|drank (?:only |about )?(?:a third|a quarter|very little)|\bcups? only\b"),
    # --- energy ---------------------------------------------------------------
    _rule("energy", r"\b(?:tired|sleepy|drowsy|dozed|dozing|lethargic|lethargy|fatigued?|exhausted)\b"
                    r"|slept (?:through|most of the (?:day|afternoon))|rested in (?:his|her)? ?room|go to bed early"
                    r"|needed prompting|\bquiet (?:this|today|all)"),
    # --- mobility -------------------------------------------------------------
    _rule("mobility", r"hands-on (?:help|assist\w*)|(?:extra|more) (?:help|assist\w*)|needed (?:help|assistance) (?:walking|to walk|transferring)"
                      r"|unable to (?:walk|stand)|difficulty walking|(?:one|two)-person assist|unsteady|shuffling|near fall|lost (?:his|her) balance"),
    # --- toileting ------------------------------------------------------------
    _rule("toileting", r"no (?:bm|bowel movement)s?\b(?:[^.]*?\bfor (\d+) days)?", sub="bowel", change="decreased", neg=False, days_group=1),
    _rule("toileting", r"constipat\w*", sub="bowel", change="decreased"),
    _rule("toileting", r"diarrh\w*|loose stools?", sub="bowel", change="increased"),
    _rule("toileting", r"voided only once|only voided once|urine (?:was |is )?dark|dark urine|(?:has not|hasn't|not) voided|decreased urine|low urine output",
          sub="urine", change="decreased", neg=False),
    _rule("toileting", r"frequent urination|voiding (?:more )?frequently|urinary urgency|more incontinen\w*|incontinent more",
          sub="urine", change="increased"),
    # --- pain -----------------------------------------------------------------
    _rule("pain", r"\bpain(?:ful)?\b|grimac\w*|wincing|\bsore\b|\baches?\b|headaches?|\bhurts?\b"
                  r"|holding (?:his|her) (?:stomach|side|head|back|abdomen)|stomach (?:feels|felt) full|complain\w* of|discomfort|uncomfortable"),
    # --- confusion ------------------------------------------------------------
    _rule("confusion", r"\bconfus\w*|disoriented|disorientation|agitated|hallucinat\w*|not making sense"),
    # --- social ---------------------------------------------------------------
    _rule("social", r"declined (?:the )?(?:afternoon |morning |evening )?(?:bingo|activit\w*|music\w*|coffee group|exercise\w*|program\w*)"
                    r"|stayed in (?:his|her) room|withdrawn|isolating"),
    # --- sleep ----------------------------------------------------------------
    _rule("sleep", r"restless night|up (?:several|many|multiple) times|awake (?:most|much|all) of the night|poor(?:ly)? sle\w*"
                   r"|did not sleep|didn't sleep|trouble sleeping", neg=False),
]

# "No", "not", "denies" ... before the symptom, in the same clause, rules it out.
NEGATION = re.compile(r"\b(?:no|not|denies|denied|without|never|didn't|did not|doesn't|does not|wasn't|isn't|free of|negative for)\b", _R)
# The note itself says this is a change from normal. "as usual" means the opposite.
COMPARATIVE = re.compile(r"than usual|unusual|usually(?! as)|which (?:he|she) usually|than before|first time", _R)

# Meal amounts, most specific first.
MEAL_CONTEXT = re.compile(r"\b(?:ate|eaten|eating|finished (?:his|her) (?:breakfast|lunch|dinner|meal)|bites?)\b", _R)
MEAL_AMOUNTS = [
    (re.compile(r"(\d{1,3})\s*%"), None),
    (re.compile(r"less than usual|eating less|poor appetite", _R), "less"),
    (re.compile(r"almost all|ate well", _R), 90),
    (re.compile(r"\ball of\b|\bate all\b|finished (?:his|her)", _R), 100),
    (re.compile(r"three quarters", _R), 75),
    (re.compile(r"two thirds", _R), 67),
    (re.compile(r"fair amount", _R), 65),
    (re.compile(r"\bmost\b", _R), 80),
    (re.compile(r"\bhalf\b", _R), 50),
    (re.compile(r"a third", _R), 33),
    (re.compile(r"a quarter|quarter of", _R), 25),
    (re.compile(r"few bites|poorly", _R), 15),
]

_SENTENCES = re.compile(r"(?<=[.!?])\s+")
_CLAUSES = re.compile(r",|;|\bbut\b", _R)


def parse_time(value: Any) -> datetime:
    if isinstance(value, datetime):
        return value
    return datetime.fromisoformat(str(value).replace("Z", "+00:00"))


def _meal(clause: str) -> Optional[Meal]:
    if not MEAL_CONTEXT.search(clause):
        return None
    for rx, value in MEAL_AMOUNTS:
        m = rx.search(clause)
        if not m:
            continue
        if value is None:
            return Meal(pct=float(m.group(1)), phrase=clause.strip())
        if value == "less":
            return Meal(pct=None, phrase=clause.strip(), said_less=True)
        return Meal(pct=float(value), phrase=clause.strip())
    return None


def extract(note: Dict[str, Any]) -> NoteFacts:
    """Read one care note. ``note`` needs ``note_text`` and ``recorded_at``."""
    facts = NoteFacts(note=note, time=parse_time(note["recorded_at"]))
    text = note.get("note_text") or ""
    for sentence in _SENTENCES.split(text):
        comparative = bool(COMPARATIVE.search(sentence))
        for clause in _CLAUSES.split(sentence):
            if not clause.strip():
                continue
            meal = _meal(clause)
            if meal:
                facts.meals.append(meal)
            for r in RULES:
                m = r["rx"].search(clause)
                if not m:
                    continue
                days = None
                if r["days_group"] and m.group(r["days_group"]):
                    days = int(m.group(r["days_group"]))
                sig = Signal(
                    category=r["category"], subcategory=r["sub"], change=r["change"],
                    phrase=sentence.strip(), urgent=r["urgent"], comparative=comparative,
                    stated_days=days,
                )
                negated = r["neg"] and NEGATION.search(clause[: m.start()])
                (facts.negated if negated else facts.signals).append(sig)
    facts.signals = _dedupe(facts.signals)
    facts.negated = _dedupe(facts.negated)
    return facts


def _dedupe(signals: List[Signal]) -> List[Signal]:
    """One signal per category per note (keep the urgent / most specific one)."""
    best: Dict[str, Signal] = {}
    for s in signals:
        cur = best.get(s.match_key)
        if cur is None or (s.urgent and not cur.urgent) or (s.stated_days and not cur.stated_days):
            best[s.match_key] = s
    return list(best.values())
