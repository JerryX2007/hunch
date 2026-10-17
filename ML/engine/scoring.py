"""Glue: pick one resident's records, run every rule, add up points, pick a tier."""

from dataclasses import dataclass
from datetime import datetime, timedelta
from functools import cache
from pathlib import Path

import yaml

from engine.models import SIGN_LABELS, Hunch, Reading, Resident
from engine.rules import RULES, Context, RuleResult

TIER_ORDER = ["Quiet", "Watch", "Assess", "Call NP"]


@cache
def load_weights(path: str | None = None) -> dict:
    p = Path(path) if path else Path(__file__).with_name("weights.yaml")
    return yaml.safe_load(p.read_text())


@dataclass(frozen=True)
class Assessment:
    resident: Resident
    score: int
    tier: str
    results: list[RuleResult]
    notes: list[str]  # context that didn't score, e.g. ignored chronic signs

    @property
    def reasons(self) -> list[str]:
        return [r.reason for r in self.results]

    def to_dict(self) -> dict:
        return {
            "resident_id": self.resident.id,
            "score": self.score,
            "tier": self.tier,
            "rules": [
                {"code": r.code, "points": r.points, "reason": r.reason,
                 "evidence": r.evidence, "red_flag": r.red_flag}
                for r in self.results
            ],
            "notes": self.notes,
        }


def dedupe(hunches: list[Hunch]) -> list[Hunch]:
    """One record per (staff, shift, sign): tapping or repeating five times adds nothing."""
    seen: dict[tuple, Hunch] = {}
    for h in sorted(hunches, key=lambda h: h.time):
        seen.setdefault((h.staff_id, h.shift, h.sign), h)
    return list(seen.values())


def tier_for(score: int, red_flag: bool, w: dict) -> str:
    t = w["tiers"]
    if red_flag or score >= t["call_np"]:
        return "Call NP"
    if score >= t["assess"]:
        return "Assess"
    if score >= t["watch"]:
        return "Watch"
    return "Quiet"


def score_resident(
    resident: Resident,
    hunches: list[Hunch],
    readings: list[Reading],
    now: datetime,
    weights: dict | None = None,
) -> Assessment:
    w = weights or load_weights()
    since = now - timedelta(hours=w["hunch_window_hours"])

    mine = [h for h in hunches if h.resident_id == resident.id and since < h.time <= now]
    chronic = [h for h in mine if h.sign in resident.chronic_signs]
    counted = dedupe([h for h in mine if h.sign not in resident.chronic_signs])
    notes = [f"Not counted: {SIGN_LABELS[s]} is usual for this resident"
             for s in sorted({h.sign for h in chronic}, key=lambda s: s.value)]
    if not resident.flu_shot_this_season:
        notes.append("Context: no flu shot recorded this season")

    ctx = Context(
        resident=resident,
        hunches=counted,
        readings=[r for r in readings if r.resident_id == resident.id],
        now=now,
        w=w,
    )
    results = [r for rule in RULES if (r := rule(ctx)) is not None]
    score = sum(r.points for r in results)
    tier = tier_for(score, any(r.red_flag for r in results), w)
    return Assessment(resident, score, tier, results, notes)


def score_unit(
    residents: list[Resident],
    hunches: list[Hunch],
    readings: list[Reading],
    now: datetime,
    weights: dict | None = None,
) -> list[Assessment]:
    """Score everyone, most urgent first. 20 residents takes milliseconds."""
    out = [score_resident(r, hunches, readings, now, weights) for r in residents]
    return sorted(out, key=lambda a: (TIER_ORDER.index(a.tier), a.score), reverse=True)
