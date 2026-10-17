"""The rules. Each one is a small pure function.

Every rule looks at one resident's Context and returns either None (didn't
fire) or a RuleResult with: points, a plain-English reason, and the IDs of the
records that justify it. Those reasons ARE the "why flagged" panel, and the
evidence IDs are what lets us check Gemini's explanation later.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Callable

from engine.baseline import baseline, latest
from engine.models import SIGN_LABELS, Hunch, Reading, Resident, Sign


@dataclass(frozen=True)
class RuleResult:
    code: str
    points: int
    reason: str
    evidence: list[str] = field(default_factory=list)
    red_flag: bool = False  # a red flag means Call NP regardless of the score


@dataclass(frozen=True)
class Context:
    resident: Resident
    hunches: list[Hunch]      # this resident's: in window, de-duplicated, chronic signs removed
    readings: list[Reading]   # this resident's charted readings
    now: datetime
    w: dict                   # contents of weights.yaml

    def base(self, kind: str) -> float | None:
        b = self.w["baseline"]
        return baseline(self.readings, kind, self.now, b["days"], b["skip_hours"], b["min_points"])


# ---------- Hunch corroboration rules ----------

def hunch_any(ctx: Context) -> RuleResult | None:
    if not ctx.hunches:
        return None
    n = len(ctx.hunches)
    return RuleResult(
        "HUNCH",
        ctx.w["points"]["hunch"],
        f"{n} staff report{'s' if n != 1 else ''} of change in the last {ctx.w['hunch_window_hours']} h",
        [h.id for h in ctx.hunches],
    )


def multi_staff(ctx: Context) -> RuleResult | None:
    staff = {h.staff_id for h in ctx.hunches}
    p = ctx.w["points"]
    pts = min((len(staff) - 1) * p["multi_staff_per_extra"], p["multi_staff_max"])
    if pts <= 0:
        return None
    return RuleResult("MULTI_STAFF", pts, f"{len(staff)} different staff noticed changes",
                      [h.id for h in ctx.hunches])


def multi_shift(ctx: Context) -> RuleResult | None:
    shifts = {h.shift for h in ctx.hunches}
    p = ctx.w["points"]
    pts = min((len(shifts) - 1) * p["multi_shift_per_extra"], p["multi_shift_max"])
    if pts <= 0:
        return None
    return RuleResult("MULTI_SHIFT", pts, f"Noticed across {len(shifts)} shifts",
                      [h.id for h in ctx.hunches])


def multi_sign(ctx: Context) -> RuleResult | None:
    signs = sorted({h.sign for h in ctx.hunches}, key=lambda s: s.value)
    if len(signs) < 2:
        return None
    labels = ", ".join(SIGN_LABELS[s] for s in signs)
    return RuleResult("MULTI_SIGN", ctx.w["points"]["multi_sign"],
                      f"More than one kind of change: {labels}", [h.id for h in ctx.hunches])


# ---------- Chart rules (published LTC thresholds) ----------

def fever(ctx: Context) -> RuleResult | None:
    t = latest(ctx.readings, "temp_c", ctx.now)
    if t is None:
        return None
    th = ctx.w["thresholds"]
    base = ctx.base("temp_c")
    if t.value > th["fever_abs_c"]:
        reason = f"Temp {t.value:.1f} °C is above {th['fever_abs_c']} °C (IDSA fever threshold)"
    elif base is not None and t.value - base > th["fever_rise_c"]:
        reason = (f"Temp {t.value:.1f} °C is {t.value - base:.1f} °C above usual {base:.1f} °C "
                  f"(IDSA: >{th['fever_rise_c']} °C over baseline counts as fever in LTC)")
    else:
        return None
    return RuleResult("FEVER", ctx.w["points"]["fever"], reason, [t.id])


def fever_with_delirium(ctx: Context) -> RuleResult | None:
    """Loeb minimum criteria: fever together with new drowsiness or confusion."""
    f = fever(ctx)
    drowsy = [h for h in ctx.hunches if h.sign in (Sign.SLEEPIER, Sign.CONFUSED)]
    if f is None or not drowsy:
        return None
    return RuleResult("FEVER_DELIRIUM", ctx.w["points"]["fever_with_delirium"],
                      "Fever together with new sleepiness or confusion (Loeb criteria)",
                      f.evidence + [h.id for h in drowsy])


def oxygen(ctx: Context) -> RuleResult | None:
    s = latest(ctx.readings, "spo2", ctx.now)
    if s is None:
        return None
    th = ctx.w["thresholds"]
    base = ctx.base("spo2")
    pts = ctx.w["points"]["spo2"]
    if s.value < th["spo2_red_flag"]:
        return RuleResult("SPO2_RED", pts, f"SpO₂ {s.value:.0f}% is below {th['spo2_red_flag']}%",
                          [s.id], red_flag=True)
    if s.value < th["spo2_low"]:
        return RuleResult("SPO2_LOW", pts, f"SpO₂ {s.value:.0f}% is below {th['spo2_low']}% (McGeer)", [s.id])
    if base is not None and base - s.value > th["spo2_drop"]:
        return RuleResult("SPO2_DROP", pts,
                          f"SpO₂ {s.value:.0f}% is {base - s.value:.0f} points below usual {base:.0f}% (McGeer: >3%)",
                          [s.id])
    return None


def fluids_low(ctx: Context) -> RuleResult | None:
    f = latest(ctx.readings, "fluids_24h", ctx.now)
    base = ctx.base("fluids_24h")
    if f is None or base is None:
        return None
    if f.value > base * ctx.w["thresholds"]["fluids_ratio"]:
        return None
    pct = (f.value / base - 1) * 100
    return RuleResult("FLUIDS_LOW", ctx.w["points"]["fluids_low"],
                      f"Fluids {f.value:.0f} mL in 24 h vs usual {base:.0f} mL ({pct:+.0f}%)", [f.id])


# Order matters only for how reasons are listed on screen.
RULES: list[Callable[[Context], RuleResult | None]] = [
    hunch_any, multi_staff, multi_shift, multi_sign,
    fever, fever_with_delirium, oxygen, fluids_low,
]
