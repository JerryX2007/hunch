"""Compare a resident's recent care notes with their own history.

The question it answers: "is this resident different from *their own* normal?"
A resident who always eats 50-70% is not flagged for eating 60%; a resident
who usually eats 90% is.

Decision, in order:
1. Urgent event in the recent window (a fall, can't bear weight, chest pain,
   short of breath, hospital transfer) -> urgent alert, no waiting.
2. Fewer than ``min_baseline_days`` days of history -> "baseline limited":
   no pattern alert, because there is no normal to compare with.
3. A category is *persisting* when it shows up on at least
   ``min_days`` different recent days AND clearly more often than in the
   resident's baseline. Two or more persisting categories -> alert.
   Exactly one -> watch.
4. Anything noted once is listed as supporting context, never a trigger.

All numbers live in THRESHOLDS: proposed, NOT clinically validated.
"""

from __future__ import annotations

import statistics
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from typing import Any, Dict, Iterable, List, Optional

from .extract import NoteFacts, Signal, extract, parse_time

THRESHOLDS = {
    "recent_days": 4,           # recent window: the last N calendar days
    "min_baseline_days": 7,     # fewer days of history -> baseline limited
    "min_days": 2,              # a category must appear on >= N recent days
    "min_rate_increase": 0.35,  # ...and on >= 35 percentage points more days than in baseline
    "meal_drop_points": 20,     # a meal is low if it's >= 20 points below the usual median
    "alert_categories": 2,      # persisting categories needed for an alert
}

LABELS = {
    "nutrition": "Eating", "fluids": "Drinking", "energy": "Energy / tiredness",
    "mobility": "Mobility", "toileting.urine": "Urine", "toileting.bowel": "Bowels",
    "pain": "Pain / discomfort", "confusion": "Confusion", "social": "Social / activities",
    "sleep": "Sleep", "breathing": "Breathing", "event": "Event",
}


@dataclass
class Evidence:
    """One note that supports a finding, for the 'why flagged' panel."""
    note_id: Optional[str]
    recorded_at: str
    author_role: Optional[str]
    note_text: str
    phrase: str
    author_name: Optional[str] = None  # signed-in nurse who wrote the note

    @classmethod
    def from_facts(cls, f: NoteFacts, phrase: str) -> "Evidence":
        n = f.note
        return cls(n.get("id"), f.time.isoformat(), n.get("author_role"), n.get("note_text", ""), phrase,
                   n.get("author_name"))


@dataclass
class Finding:
    key: str                      # e.g. "nutrition", "toileting.bowel"
    match_key: str                # e.g. "toileting.bowel.decreased"
    persisting: bool
    recent_days: List[str]        # ISO dates
    baseline_rate: float          # share of baseline days with this signal
    recent_rate: float
    reason: str
    urgent: bool = False
    signals: List[Signal] = field(default_factory=list)
    evidence: List[Evidence] = field(default_factory=list)


@dataclass
class HistoryCheck:
    resident_id: str
    as_of: str
    tier: str                     # quiet | watch | alert | urgent | baseline_limited
    alert: bool
    urgent: bool
    baseline_limited: bool
    baseline_days: int
    window: Dict[str, str]
    findings: List[Finding]
    reasons: List[str]
    ruled_out: List[str]          # negated mentions, e.g. "pain (denied)"

    @property
    def categories(self) -> List[str]:
        return [f.key for f in self.findings]

    @property
    def match_signals(self) -> List[str]:
        return sorted({f.match_key for f in self.findings if f.key != "event"})

    @property
    def match_weights(self) -> Dict[str, float]:
        """Signals for case matching: persisting/urgent weigh 1, one-off notes 0.5."""
        w: Dict[str, float] = {}
        for f in self.findings:
            if f.key == "event":
                continue
            v = 1.0 if (f.persisting or f.urgent) else 0.5
            w[f.match_key] = max(w.get(f.match_key, 0.0), v)
        return dict(sorted(w.items()))

    @property
    def duration_days(self) -> int:
        """Days from the first recent finding to as_of (or longer if a note states it)."""
        firsts = [min(f.recent_days) for f in self.findings if f.recent_days]
        if not firsts:
            return 1
        span = (date.fromisoformat(self.as_of[:10]) - date.fromisoformat(min(firsts))).days + 1
        stated = [s.stated_days for f in self.findings for s in f.signals if s.stated_days]
        return max([span] + stated)

    @property
    def title(self) -> str:
        if self.urgent:
            urgent = [f for f in self.findings if f.urgent]
            symptom = next((f for f in urgent if f.key != "event"), None)
            what = LABELS.get(symptom.key, symptom.key).lower() if symptom else "serious"
            extra = " (hospital transfer)" if any(f.key == "event" for f in urgent) else ""
            return f"Urgent: {what} event{extra}"
        keys = [LABELS.get(f.key, f.key).lower() for f in self.findings if f.persisting]
        return "Change from usual: " + ", ".join(keys)


def _day(dt: datetime) -> date:
    return dt.date()


def check_resident(
    resident: Dict[str, Any],
    notes: Iterable[Dict[str, Any]],
    as_of: Optional[datetime] = None,
    thresholds: Optional[Dict[str, float]] = None,
) -> HistoryCheck:
    """Run the history check for one resident.

    ``resident`` needs ``id``; ``baseline_start`` / ``baseline_end`` are used when present.
    ``notes`` are that resident's care notes (``note_text``, ``recorded_at``; ``id`` and
    ``author_role`` are carried into the evidence when present).
    ``as_of`` defaults to the newest note's time, so the result doesn't drift with the clock.
    """
    t = {**THRESHOLDS, **(thresholds or {})}
    facts = sorted((extract(n) for n in notes), key=lambda f: f.time)
    rid = resident["id"]
    if not facts:
        return HistoryCheck(rid, (as_of or datetime.now()).isoformat(), "baseline_limited", False, False,
                            True, 0, {}, [], ["No care notes recorded yet."], [])

    as_of = as_of or facts[-1].time
    recent_start = _day(as_of) - timedelta(days=int(t["recent_days"]) - 1)
    b0 = date.fromisoformat(str(resident["baseline_start"])[:10]) if resident.get("baseline_start") else None
    b1 = date.fromisoformat(str(resident["baseline_end"])[:10]) if resident.get("baseline_end") else None
    b1 = min(b1, recent_start - timedelta(days=1)) if b1 else recent_start - timedelta(days=1)

    recent = [f for f in facts if recent_start <= _day(f.time) <= _day(as_of)]
    baseline = [f for f in facts if (b0 is None or _day(f.time) >= b0) and _day(f.time) <= b1]
    baseline_dates = sorted({_day(f.time) for f in baseline})
    recent_dates = sorted({_day(f.time) for f in recent})
    n_base, n_recent = len(baseline_dates), max(len(recent_dates), 1)
    limited = n_base < t["min_baseline_days"]

    findings: List[Finding] = []

    # --- text signals, per category ------------------------------------------
    by_key_recent: Dict[str, List[tuple]] = defaultdict(list)
    for f in recent:
        for s in f.signals:
            by_key_recent[s.match_key].append((f, s))
    base_days_with: Dict[str, set] = defaultdict(set)
    for f in baseline:
        for s in f.signals:
            base_days_with[s.match_key].add(_day(f.time))

    for mkey, hits in by_key_recent.items():
        s0 = hits[0][1]
        days = sorted({_day(f.time).isoformat() for f, _ in hits})
        b_rate = len(base_days_with[mkey]) / n_base if n_base else 0.0
        r_rate = len(days) / n_recent
        urgent = any(s.urgent for _, s in hits)
        persisting = (not limited and len(days) >= t["min_days"]
                      and r_rate - b_rate >= t["min_rate_increase"])
        label = LABELS.get(s0.key, s0.key)
        change = f" ({s0.change})" if s0.change else ""
        if persisting:
            reason = (f"{label}{change}: noted on {len(days)} of the last {n_recent} days "
                      f"vs {len(base_days_with[mkey])} of {n_base} usual days.")
        else:
            reason = f"{label}{change}: noted once ({days[0]}): \"{s0.phrase}\""
        stated = max((s.stated_days or 0) for _, s in hits)
        if stated:
            reason += f" Note states {stated} days."
        if any(s.comparative for _, s in hits):
            reason += " Staff wrote that this is unusual for the resident."
        if urgent:
            ev = next(s for _, s in hits if s.urgent)
            reason = f"URGENT - {label}: \"{ev.phrase}\" ({_day(next(f for f, s in hits if s.urgent).time)})"
        findings.append(Finding(
            key=s0.key, match_key=mkey, persisting=persisting, recent_days=days,
            baseline_rate=round(b_rate, 2), recent_rate=round(r_rate, 2), reason=reason, urgent=urgent,
            signals=[s for _, s in hits], evidence=[Evidence.from_facts(f, s.phrase) for f, s in hits],
        ))

    # --- meals, against the resident's own usual intake ----------------------
    base_pcts = [m.pct for f in baseline for m in f.meals if m.pct is not None]
    if base_pcts:
        usual = statistics.median(base_pcts)
        lowest_usual = min(base_pcts)
        cutoff = min(usual - t["meal_drop_points"], lowest_usual)  # strictly below both
        base_low_days = {_day(f.time) for f in baseline for m in f.meals
                         if m.said_less or (m.pct is not None and m.pct < cutoff)}
        low = [(f, m) for f in recent for m in f.meals
               if m.said_less or (m.pct is not None and m.pct < cutoff)]
        all_recent = [m for f in recent for m in f.meals]
        if low:
            days = sorted({_day(f.time).isoformat() for f, _ in low})
            b_rate = len(base_low_days) / n_base if n_base else 0.0
            r_rate = len(days) / n_recent
            persisting = (not limited and len(days) >= t["min_days"]
                          and r_rate - b_rate >= t["min_rate_increase"])
            recent_pcts = [m.pct for m in all_recent if m.pct is not None]
            if persisting:
                reason = (f"Eating: {len(low)} of {len(all_recent)} recent meals below this resident's usual "
                          f"(usual median {usual:.0f}%, lowest usual {lowest_usual:.0f}%); "
                          f"recent median {statistics.median(recent_pcts):.0f}% across {len(days)} days.")
            else:
                f, m = low[0]
                reason = (f"Eating: one low meal ({days[0]}): \"{m.phrase}\" "
                          f"(usual median {usual:.0f}%).")
            findings.append(Finding(
                key="nutrition", match_key="nutrition", persisting=persisting, recent_days=days,
                baseline_rate=round(b_rate, 2), recent_rate=round(r_rate, 2), reason=reason,
                evidence=[Evidence.from_facts(f, m.phrase) for f, m in low],
            ))

    # --- decision -------------------------------------------------------------
    urgent = any(f.urgent for f in findings)
    persisting = [f for f in findings if f.persisting]
    if urgent:
        tier = "urgent"
    elif limited:
        tier = "baseline_limited"
    elif len(persisting) >= t["alert_categories"]:
        tier = "alert"
    elif persisting:
        tier = "watch"
    else:
        tier = "quiet"
    alert = tier in ("urgent", "alert")

    findings.sort(key=lambda f: (not f.urgent, not f.persisting, -len(f.recent_days), f.key))
    reasons = [f.reason for f in findings if f.urgent or f.persisting]
    context = [f.reason for f in findings if not (f.urgent or f.persisting)]
    if limited:
        reasons.insert(0, f"Only {n_base} day(s) of history before the recent window "
                          f"(need {t['min_baseline_days']}); can't tell what's usual yet.")
    if not alert and not reasons:
        reasons.append("No lasting change from this resident's usual pattern."
                       + (" One-off notes:" if context else ""))
    if alert and context:
        reasons.append("Also noted once: " + "; ".join(c.split(":")[0] for c in context) + ".")
    elif not alert:
        reasons.extend(context)

    ruled_out = sorted({f"{s.key} (ruled out in notes)" for f in recent for s in f.negated})
    return HistoryCheck(
        resident_id=rid, as_of=as_of.isoformat(), tier=tier, alert=alert, urgent=urgent,
        baseline_limited=limited, baseline_days=n_base,
        window={"baseline_start": (baseline_dates[0].isoformat() if baseline_dates else None),
                "baseline_end": (baseline_dates[-1].isoformat() if baseline_dates else None),
                "recent_start": recent_start.isoformat(), "recent_end": _day(as_of).isoformat()},
        findings=findings, reasons=reasons, ruled_out=ruled_out,
    )


def check_unit(residents: List[Dict[str, Any]], notes: List[Dict[str, Any]],
               as_of: Optional[datetime] = None) -> List[HistoryCheck]:
    """Run every resident with one shared as_of (newest note on the unit)."""
    if as_of is None and notes:
        as_of = max(parse_time(n["recorded_at"]) for n in notes)
    by_res: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    for n in notes:
        by_res[n["resident_id"]].append(n)
    order = {"urgent": 0, "alert": 1, "watch": 2, "baseline_limited": 3, "quiet": 4}
    out = [check_resident(r, by_res.get(r["id"], []), as_of) for r in residents]
    return sorted(out, key=lambda c: (order[c.tier], c.resident_id))
