"""Generate CareSignal seed files: residents, notes, cases, eval scenarios.

Deterministic (fixed random seed). Run: python generate_seed.py
Cases are hand-written in cases.json (loaded by seed_cases.py).
Writes residents.json, notes.json, cases.json and eval_scenarios.json next to this file.
All data is fictional.
"""
import json
import random
from datetime import date, datetime, timedelta
from pathlib import Path

rng = random.Random(42)
OUT = Path(__file__).parent

HISTORY_START = date(2026, 9, 20)
BASELINE_END = date(2026, 10, 10)
RECENT_START = date(2026, 10, 14)
LAST_DAY = date(2026, 10, 17)

# ---------------------------------------------------------------- residents
PROFILES = {
    "DEMO-011": dict(scenario="stable", sex="F", meal=(80, 100), mob="a walker", activity="the music program"),
    "DEMO-012": dict(scenario="stable", sex="M", meal=(75, 100), mob="a cane", activity="chair exercises"),
    "DEMO-013": dict(scenario="stable", sex="F", meal=(80, 100), mob="standby assist", activity="bingo"),
    "DEMO-014": dict(scenario="planted_decline", sex="F", meal=(80, 100), mob="standby assist", activity="bingo"),
    "DEMO-015": dict(scenario="negation_test", sex="M", meal=(75, 100), mob="a walker", activity="exercise class"),
    "DEMO-016": dict(scenario="short_history", sex="F", meal=(70, 100), mob="a walker", activity="the music program",
                     start=date(2026, 10, 12), baseline=(date(2026, 10, 12), date(2026, 10, 13))),
    "DEMO-017": dict(scenario="urgent_symptom", sex="M", meal=(75, 100), mob="a walker", activity="the coffee group"),
    "DEMO-018": dict(scenario="isolated_dip", sex="F", meal=(80, 100), mob="a cane", activity="chair exercises"),
    "DEMO-019": dict(scenario="planted_decline", sex="M", meal=(80, 100), mob="standby assist", activity="bingo"),
    "DEMO-020": dict(scenario="stable", sex="F", meal=(50, 70), mob="a walker", activity="the music program", low_eater=True),
    "DEMO-021": dict(scenario="isolated_dip", sex="M", meal=(80, 100), mob="a cane", activity="bingo"),
    "DEMO-022": dict(scenario="constipation_pattern", sex="F", meal=(80, 100), mob="a walker", activity="the coffee group",
                     no_bm_from=date(2026, 10, 12)),
}

# ---------------------------------------------------------------- phrasing
BUCKETS = [100, 90, 80, 75, 70, 60, 50, 40, 30, 25]


def meal_phrase(pct, meal, pr):
    his = "her" if pr == "she" else "his"
    if pct == 100:
        opts = [f"Ate all of {meal}.", f"Finished {his} {meal}.", f"Ate 100% of {meal}."]
    elif pct == 90:
        opts = [f"Ate almost all of {meal}.", f"Ate 90% of {meal}.", f"Ate well at {meal}."]
    elif pct in (80, 75):
        opts = [f"Ate about three quarters of {meal}.", f"Ate {pct}% of {meal}.", f"Ate most of {meal}."]
    elif pct in (70, 60):
        opts = [f"Ate about two thirds of {meal}.", f"Ate {pct}% of {meal}.", f"Ate a fair amount of {meal}."]
    elif pct == 50:
        opts = [f"Ate about half of {meal}.", f"Ate 50% of {meal}.", f"Ate half {his} {meal}."]
    else:
        opts = [f"Ate about {pct}% of {meal}.", f"Ate poorly at {meal}.", f"Only a few bites of {meal}."]
    return rng.choice(opts)


ENERGY_OK = [
    "Alert and chatty during morning activities.",
    "Bright and engaged this morning.",
    "In good spirits, chatting with tablemates.",
    "Awake and alert for morning care.",
]
NIGHT_OK = [
    "Slept well overnight.",
    "Up once to the bathroom, settled back to sleep.",
    "Repositioned at 0200, slept between checks.",
    "Incontinent of urine once, brief changed, settled back to sleep.",
]
FLUIDS_OK = [
    "Drank 2 cups of juice and water.",
    "Good fluid intake.",
    "Drank about 250 mL.",
    "Finished tea and a glass of water.",
]
URINE_OK = [
    "Toileted with assist, voided.",
    "Voided x2 this shift.",
    "Continent of urine, toileted before meal.",
]
BOWEL_OK = [
    "BM this morning, formed.",
    "Had a bowel movement, normal.",
    "Small formed BM.",
]
SOCIAL_OK = [
    "Chatted with tablemates.",
    "Visited with family in the lounge.",
    "Sat with friends in the lounge.",
]
ORIENTED_OK = [
    "Oriented, knew the day of the week.",
    "Following conversation well.",
]
NEGATIONS = [
    "Denies shortness of breath.",
    "Denies pain.",
    "No signs of fatigue today.",
    "No difficulty walking.",
    "No complaints of pain.",
    "Not confused, oriented to place.",
    "No diarrhea.",
]


def mob_ok(mob):
    return rng.choice([
        f"Walked to dining room with {mob}.",
        f"Ambulated with {mob}, steady.",
        f"Walked back to room with {mob}.",
    ])


def stamp(d, h0, h1):
    minute = rng.randrange(h0 * 60, h1 * 60)
    minute -= minute % 5
    return datetime(d.year, d.month, d.day, minute // 60, minute % 60).isoformat()


def normal_pct(p):
    lo, hi = p["meal"]
    choices = [b for b in BUCKETS if lo <= b <= hi]
    if rng.random() < 0.05:  # natural variation: one bucket below usual range
        floor = 40 if p.get("low_eater") else 60
        below = [b for b in BUCKETS if floor <= b < lo]
        if below:
            return max(below)
    return rng.choice(choices)


def normal_day(rid, p, d):
    pr = "she" if p["sex"] == "F" else "he"
    notes = []

    def add(ts, text, role=None):
        notes.append(dict(resident_id=rid, recorded_at=ts,
                          author_role=role or ("nurse" if rng.random() < 0.2 else "PSW"),
                          note_text=text))

    parts = [meal_phrase(normal_pct(p), "breakfast", pr)]
    if rng.random() < 0.4:
        parts.append(rng.choice(FLUIDS_OK))
    if rng.random() < 0.5:
        parts.append(rng.choice(ENERGY_OK))
    if rng.random() < 0.1:
        parts.append(rng.choice(ORIENTED_OK))
    if rng.random() < 0.35:
        parts.append(mob_ok(p["mob"]))
    add(stamp(d, 7, 9), " ".join(parts))

    extra = rng.sample(["lunch", "dinner", "night"], k=rng.choice([1, 2, 2]))
    if d == LAST_DAY:  # day not over yet: breakfast and lunch only
        extra = ["lunch"]
    for slot in extra:
        if slot == "lunch":
            parts = [meal_phrase(normal_pct(p), "lunch", pr)]
            if rng.random() < 0.3:
                parts.append(rng.choice(FLUIDS_OK))
            if rng.random() < 0.25:
                parts.append(rng.choice(URINE_OK))
            if rng.random() < 0.3:
                parts.append(mob_ok(p["mob"]))
            add(stamp(d, 12, 13), " ".join(parts))
        elif slot == "dinner":
            parts = [meal_phrase(normal_pct(p), "dinner", pr)]
            if rng.random() < 0.25:
                parts.append(rng.choice(SOCIAL_OK))
            if rng.random() < 0.35:
                parts.append(f"Joined {p['activity']} after dinner.")
            add(stamp(d, 18, 20), " ".join(parts))
        else:
            add(stamp(d, 2, 5), rng.choice(NIGHT_OK), role="PSW")

    # Bowel movement roughly every 1-2 days, unless the scenario stops them.
    no_bm_from = p.get("no_bm_from")
    if rng.random() < 0.55 and not (no_bm_from and d >= no_bm_from):
        target = rng.choice([x for x in notes if int(x["recorded_at"][11:13]) >= 6])
        target["note_text"] += " " + rng.choice(BOWEL_OK)
    return notes


# ------------------------------------------------- scripted recent windows
def n(rid, ts, role, text):
    return dict(resident_id=rid, recorded_at=ts, author_role=role, note_text=text)


SCRIPTED = {
    "DEMO-014": [
        n("DEMO-014", "2026-10-14T08:15:00", "PSW", "Ate about half of breakfast. Seemed more tired than usual during morning activities."),
        n("DEMO-014", "2026-10-14T12:35:00", "PSW", "Ate about 60% of lunch. Walked to dining room with standby assist."),
        n("DEMO-014", "2026-10-14T18:20:00", "PSW", "Ate most of dinner. Asked to go to bed early."),
        n("DEMO-014", "2026-10-15T08:40:00", "PSW", "Ate 50% of breakfast. Quiet this morning."),
        n("DEMO-014", "2026-10-15T12:30:00", "nurse", "Ate less than usual at lunch. Drinking less than usual, left most of her juice. Dozed in chair after lunch, which is unusual for her."),
        n("DEMO-014", "2026-10-16T08:20:00", "PSW", "Ate about 40% of breakfast. Tired, needed prompting to finish."),
        n("DEMO-014", "2026-10-16T12:40:00", "nurse", "Ate about 40% of lunch. Needed hands-on help walking to dining room, usually only standby. Declined afternoon bingo."),
        n("DEMO-014", "2026-10-16T19:00:00", "PSW", "Ate poorly at dinner, a few bites only. Needed hands-on help to walk back to room. Voided only once this shift, urine dark."),
        n("DEMO-014", "2026-10-17T08:30:00", "PSW", "Ate about a quarter of breakfast. Drank about a third of her morning fluids. Very sleepy during morning care. Needed hands-on assist walking."),
    ],
    "DEMO-019": [
        n("DEMO-019", "2026-10-14T08:30:00", "PSW", "Ate about 60% of breakfast. Walked to dining room with standby assist."),
        n("DEMO-019", "2026-10-14T12:20:00", "PSW", "Ate half his lunch. Seemed tired, rested in room after."),
        n("DEMO-019", "2026-10-15T08:10:00", "PSW", "Ate poorly at breakfast. Drowsy during morning care."),
        n("DEMO-019", "2026-10-15T12:45:00", "nurse", "Ate about 40% of lunch. Slept through most of the afternoon. Walked with standby assist as usual."),
        n("DEMO-019", "2026-10-16T08:35:00", "PSW", "Ate about half of breakfast. More tired than usual."),
        n("DEMO-019", "2026-10-16T18:30:00", "PSW", "Ate 50% of dinner. Declined bingo, which he usually attends."),
        n("DEMO-019", "2026-10-17T08:25:00", "PSW", "Ate 40% of breakfast. Sleepy but walked to dining room with standby assist."),
    ],
    "DEMO-015": [
        n("DEMO-015", "2026-10-14T08:20:00", "nurse", "Denies shortness of breath. Ate well."),
        n("DEMO-015", "2026-10-14T12:30:00", "PSW", "Ate most of lunch. Walked to dining room with a walker."),
        n("DEMO-015", "2026-10-15T08:45:00", "PSW", "Not tired today, joined exercise class. Ate all of breakfast."),
        n("DEMO-015", "2026-10-15T18:15:00", "PSW", "Ate 90% of dinner. No diarrhea, no complaints of pain."),
        n("DEMO-015", "2026-10-16T12:25:00", "PSW", "No difficulty walking, did not need extra help to the dining room. Ate all of lunch."),
        n("DEMO-015", "2026-10-16T19:10:00", "PSW", "Ate 75% of dinner. Daughter visited."),
        n("DEMO-015", "2026-10-17T08:10:00", "nurse", "Denies pain or fatigue. Not confused, oriented to place. Ate 90% of breakfast."),
        n("DEMO-015", "2026-10-17T12:35:00", "PSW", "Ate most of lunch."),
    ],
    "DEMO-017": [
        n("DEMO-017", "2026-10-14T08:25:00", "PSW", "Ate all of breakfast. Walked to dining room with a walker."),
        n("DEMO-017", "2026-10-14T12:40:00", "PSW", "Ate 80% of lunch."),
        n("DEMO-017", "2026-10-15T08:05:00", "PSW", "Ate most of breakfast. Alert and chatty during morning activities."),
        n("DEMO-017", "2026-10-15T18:30:00", "PSW", "Ate 90% of dinner. Joined the coffee group after dinner."),
        n("DEMO-017", "2026-10-16T03:10:00", "nurse", "Found on floor beside bed at 0300. Unable to bear weight on right leg and grimacing when right hip moved. RN assessed, NP called."),
        n("DEMO-017", "2026-10-16T08:30:00", "PSW", "Stayed in bed for breakfast per nurse. Ate about half."),
        n("DEMO-017", "2026-10-16T11:15:00", "nurse", "Transferred to hospital for assessment of right hip."),
    ],
    "DEMO-022": [
        n("DEMO-022", "2026-10-14T08:30:00", "PSW", "Ate 75% of breakfast. No BM again today."),
        n("DEMO-022", "2026-10-14T12:40:00", "PSW", "Ate most of lunch. Good fluid intake."),
        n("DEMO-022", "2026-10-15T08:20:00", "PSW", "Ate about 60% of breakfast. No BM since Oct 12."),
        n("DEMO-022", "2026-10-15T18:30:00", "PSW", "Ate about half of dinner. Said her stomach feels full."),
        n("DEMO-022", "2026-10-16T08:40:00", "nurse", "No BM for 4 days. Holding her stomach when standing. Ate 50% of breakfast."),
        n("DEMO-022", "2026-10-16T12:30:00", "PSW", "Ate poorly at lunch. Drank 1 cup only."),
        n("DEMO-022", "2026-10-17T08:15:00", "PSW", "No BM for 5 days. Ate a few bites of breakfast. Declined the coffee group."),
    ],
    "DEMO-018": [
        n("DEMO-018", "2026-10-15T08:30:00", "PSW", "Ate all of breakfast. Tired this morning after a restless night, perked up by lunch."),
    ],
    "DEMO-021": [
        n("DEMO-021", "2026-10-15T12:30:00", "PSW", "Ate about 30% of lunch. Said he had a big breakfast and wasn't hungry. Walked with a cane, cheerful."),
    ],
    "DEMO-016": [
        n("DEMO-016", "2026-10-16T12:30:00", "PSW", "Ate about 60% of lunch. Still settling in, asked about her daughter."),
    ],
}
# Residents whose whole recent window is scripted (others get generated notes plus their scripted ones).
FULLY_SCRIPTED = {"DEMO-014", "DEMO-019", "DEMO-015", "DEMO-017", "DEMO-022"}
FIXED_BASELINE = [  # the example note from the spec, kept verbatim
    n("DEMO-014", "2026-09-22T08:30:00", "PSW",
      "Ate all of breakfast. Alert and chatty during morning activities. Walked to dining room with standby assist."),
]


def build_notes():
    out = []
    for rid, p in PROFILES.items():
        start = p.get("start", HISTORY_START)
        d = start
        neg_days = set(rng.sample(range((BASELINE_END - start).days + 1), k=2)) if start < BASELINE_END else set()
        while d <= LAST_DAY:
            if rid in FULLY_SCRIPTED and d >= RECENT_START:
                d += timedelta(days=1)
                continue
            day_notes = normal_day(rid, p, d)
            if rid == "DEMO-014" and d == date(2026, 9, 22):
                day_notes = FIXED_BASELINE + day_notes[1:]  # replace the generated breakfast note
            if (d - start).days in neg_days:  # a negation note inside the baseline
                day_notes[-1]["note_text"] = rng.choice(NEGATIONS) + " " + day_notes[-1]["note_text"]
            # scripted single notes replace that slot's generated note
            for s in SCRIPTED.get(rid, []):
                if rid not in FULLY_SCRIPTED and s["recorded_at"][:10] == d.isoformat():
                    hour = int(s["recorded_at"][11:13])
                    nearest = min(day_notes, key=lambda x: abs(int(x["recorded_at"][11:13]) - hour))
                    day_notes = [x for x in day_notes if x is not nearest] + [s]
            out.extend(day_notes)
            d += timedelta(days=1)
        if rid in FULLY_SCRIPTED:
            out.extend(SCRIPTED[rid])
    out.sort(key=lambda x: (x["resident_id"], x["recorded_at"]))
    return out


def build_residents():
    rows = []
    for rid, p in PROFILES.items():
        b0, b1 = p.get("baseline", (HISTORY_START, BASELINE_END))
        rows.append(dict(id=rid, display_name=rid, baseline_start=b0.isoformat(),
                         baseline_end=b1.isoformat(), scenario=p["scenario"]))
    return rows


# ---------------------------------------------------------------- cases
import sys  # noqa: E402

sys.path.insert(0, str(Path(__file__).parent))
from seed_cases import CASES, CATEGORIES, SUBCATEGORIES, CHANGES, signal_key  # noqa: E402

# ---------------------------------------------------------------- eval scenarios
EVAL = [
    dict(resident_id="DEMO-011", scenario="stable", expected=dict(alert_created=False, reason="normal variation within usual range")),
    dict(resident_id="DEMO-012", scenario="stable", expected=dict(alert_created=False, reason="normal variation within usual range")),
    dict(resident_id="DEMO-013", scenario="stable", expected=dict(alert_created=False, reason="normal variation within usual range")),
    dict(resident_id="DEMO-014", scenario="planted_decline",
         expected=dict(alert_created=True,
                       categories=["nutrition", "fluids", "energy", "mobility", "toileting.urine"],
                       min_similar_cases=2)),
    dict(resident_id="DEMO-015", scenario="negation_test",
         expected=dict(alert_created=False, reason="negated symptoms only",
                       must_not_extract=[dict(category="energy", direction="worsening"),
                                         dict(category="mobility", direction="worsening"),
                                         dict(category="pain", direction="worsening"),
                                         dict(category="confusion", direction="worsening"),
                                         dict(category="toileting", subcategory="bowel", change="increased")])),
    dict(resident_id="DEMO-016", scenario="short_history",
         expected=dict(alert_created=False, baseline_limited=True, reason="fewer than 7 days of history")),
    dict(resident_id="DEMO-017", scenario="urgent_symptom",
         expected=dict(alert_created=True, urgent=True, categories=["mobility"],
                       reason="single serious event must not wait for pattern accumulation")),
    dict(resident_id="DEMO-018", scenario="isolated_dip", expected=dict(alert_created=False, reason="single tired morning with an explanation")),
    dict(resident_id="DEMO-019", scenario="planted_decline",
         expected=dict(alert_created=True, categories=["nutrition", "energy"], min_similar_cases=2)),
    dict(resident_id="DEMO-020", scenario="stable",
         expected=dict(alert_created=False, reason="intake of 50-70% matches this resident's own low baseline")),
    dict(resident_id="DEMO-021", scenario="isolated_dip", expected=dict(alert_created=False, reason="single low meal only")),
    dict(resident_id="DEMO-022", scenario="constipation_pattern",
         expected=dict(alert_created=True, categories=["toileting.bowel", "nutrition", "pain"],
                       min_similar_cases=2, reason="no bowel movement for 5 days with eating less and abdominal discomfort")),
]


# ---------------------------------------------------------------- checks
def check(residents, notes, cases):
    ids = {r["id"] for r in residents}
    assert all(x["resident_id"] in ids for x in notes)
    assert len({c["id"] for c in cases}) == len(cases) == 70
    assert {"CASE-007", "CASE-012"} <= {c["id"] for c in cases}
    used = set()
    for c in cases:
        keys = {signal_key(o) for o in c["observations"]}
        used |= keys
        assert len(keys) == len(c["observations"]), c["id"]          # no duplicate signals
        assert 1 <= len(keys) <= 5, c["id"]
        for o in c["observations"] + c["timeline"]:
            assert o["category"] in CATEGORIES, c["id"]
            if o["category"] in SUBCATEGORIES:
                assert o.get("subcategory") in SUBCATEGORIES[o["category"]], c["id"]
                assert o.get("change") in CHANGES, c["id"]
            else:
                assert "subcategory" not in o, c["id"]
        assert {signal_key(t) for t in c["timeline"]} == keys, c["id"]
        assert 2 <= c["duration_days"] <= 7 and c["limitations"] and c["documented_outcome"]
        assert all(t["day"] <= c["duration_days"] for t in c["timeline"]), c["id"]
        worsening = c["observations"][0]["direction"] == "worsening"
        assert (c["outcome_category"] is not None) == worsening, c["id"]  # labelled iff worsening
    expected = set(CATEGORIES) - {"toileting"} | {"toileting.urine", "toileting.bowel"}
    assert used == expected, expected - used                              # every signal appears
    for r in residents:
        own = [x for x in notes if x["resident_id"] == r["id"]]
        days = {x["recorded_at"][:10] for x in own}
        per_day = [sum(1 for x in own if x["recorded_at"][:10] == d) for d in days]
        assert max(per_day) <= 3 or r["id"] in FULLY_SCRIPTED, r["id"]
    # isolated-dip resident: exactly one meal below 60% in the whole record
    low = [x for x in notes if x["resident_id"] == "DEMO-021" and any(s in x["note_text"] for s in ("30%", "40%", "25%", "poorly", "few bites", "half"))]
    assert len(low) == 1, low
    # constipation resident: no BM recorded from Oct 12 onward
    assert not [x for x in notes if x["resident_id"] == "DEMO-022" and x["recorded_at"] >= "2026-10-12"
                and any(b in x["note_text"] for b in ("BM this", "bowel movement, normal", "formed BM"))]


# ---------------------------------------------------------------- people (people.json)
PEOPLE = json.loads((Path(__file__).parent / "people.json").read_text(encoding="utf-8"))


def name_people(residents, notes, evals):
    """Swap the internal DEMO-0xx keys for unit IDs + names, and give each note one of
    the unit's nurses (random, but the same every run). Note text is unchanged."""
    ids = {r["old_id"]: r for r in PEOPLE["residents"]}
    nurses = [n["name"] for n in PEOPLE["nurses"]]
    pick = random.Random(2026)
    residents = [{**r, "id": ids[r["id"]]["id"], "display_name": ids[r["id"]]["name"]} for r in residents]
    notes = [{**n, "resident_id": ids[n["resident_id"]]["id"], "author_name": pick.choice(nurses)} for n in notes]
    evals = [{**e, "resident_id": ids[e["resident_id"]]["id"]} for e in evals]
    return residents, notes, evals


def main():
    OUT.mkdir(exist_ok=True)
    residents, notes = build_residents(), build_notes()
    check(residents, notes, CASES)
    residents, notes, evals = name_people(residents, notes, EVAL)
    for name, data in [("residents", residents), ("notes", notes), ("cases", CASES), ("eval_scenarios", evals)]:
        (OUT / f"{name}.json").write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n")
    print(f"{len(residents)} residents, {len(notes)} notes, {len(CASES)} cases, {len(EVAL)} eval scenarios")


if __name__ == "__main__":
    main()
