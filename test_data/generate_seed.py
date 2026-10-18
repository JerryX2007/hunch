"""Generate CareSignal seed files: residents, notes, vitals, cases, eval scenarios.

Deterministic (fixed random seed). Run: python generate_seed.py
Cases are hand-written in cases.json (loaded by seed_cases.py).
Writes residents.json, notes.json, vitals.json, cases.json and eval_scenarios.json next to this file.
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
# v = the resident's usual vitals: temp (C), SpO2 (%), pulse, breathing rate, BP (sys, dia).
# conditions = medical history shown on the profile (context only; Hunch never diagnoses).
PROFILES = {
    "DEMO-011": dict(scenario="stable", sex="F", meal=(80, 100), mob="a walker", activity="the music program",
                     conditions=["Alzheimer's dementia (moderate)", "Osteoarthritis", "Hypertension"],
                     v=dict(t=36.6, o2=96, p=74, rr=18, bp=(132, 78))),
    "DEMO-012": dict(scenario="stable", sex="M", meal=(75, 100), mob="a cane", activity="chair exercises",
                     conditions=["Type 2 diabetes", "Hypertension", "Hearing loss"],
                     v=dict(t=36.5, o2=96, p=70, rr=16, bp=(138, 80))),
    "DEMO-013": dict(scenario="stable", sex="F", meal=(80, 100), mob="standby assist", activity="bingo",
                     conditions=["Vascular dementia", "Atrial fibrillation"],
                     v=dict(t=36.7, o2=97, p=80, rr=18, bp=(124, 72))),
    "DEMO-014": dict(scenario="planted_decline", sex="F", meal=(80, 100), mob="standby assist", activity="bingo",
                     conditions=["Alzheimer's dementia (mild)", "Osteoporosis", "Hypothyroidism"],
                     v=dict(t=36.2, o2=96, p=72, rr=18, bp=(126, 74))),
    "DEMO-015": dict(scenario="negation_test", sex="M", meal=(75, 100), mob="a walker", activity="exercise class",
                     conditions=["Parkinson's disease", "Benign prostatic hyperplasia"],
                     v=dict(t=36.6, o2=97, p=68, rr=16, bp=(130, 76))),
    "DEMO-016": dict(scenario="short_history", sex="F", meal=(70, 100), mob="a walker", activity="the music program",
                     start=date(2026, 10, 12), baseline=(date(2026, 10, 12), date(2026, 10, 13)),
                     conditions=["Mixed dementia", "Hip fracture (2025, healed)"],
                     v=dict(t=36.6, o2=96, p=76, rr=18, bp=(134, 78))),
    "DEMO-017": dict(scenario="urgent_symptom", sex="M", meal=(75, 100), mob="a walker", activity="the coffee group",
                     conditions=["Osteoporosis", "Hypertension", "History of falls"],
                     v=dict(t=36.5, o2=96, p=72, rr=18, bp=(142, 82))),
    "DEMO-018": dict(scenario="isolated_dip", sex="F", meal=(80, 100), mob="a cane", activity="chair exercises",
                     conditions=["Heart failure", "Macular degeneration"],
                     v=dict(t=36.6, o2=95, p=78, rr=18, bp=(118, 70))),
    "DEMO-019": dict(scenario="planted_decline", sex="M", meal=(80, 100), mob="standby assist", activity="bingo",
                     conditions=["Type 2 diabetes", "Chronic kidney disease (stage 3)"],
                     v=dict(t=36.5, o2=96, p=74, rr=18, bp=(136, 80))),
    "DEMO-020": dict(scenario="stable", sex="F", meal=(50, 70), mob="a walker", activity="the music program", low_eater=True,
                     conditions=["Alzheimer's dementia (advanced)", "Dysphagia (minced diet)"],
                     v=dict(t=36.4, o2=96, p=76, rr=18, bp=(118, 68))),
    "DEMO-021": dict(scenario="isolated_dip", sex="M", meal=(80, 100), mob="a cane", activity="bingo",
                     conditions=["COPD (mild)", "Hypertension"],
                     v=dict(t=36.6, o2=95, p=76, rr=18, bp=(140, 82))),
    "DEMO-022": dict(scenario="constipation_pattern", sex="F", meal=(80, 100), mob="a walker", activity="the coffee group",
                     no_bm_from=date(2026, 10, 12),
                     conditions=["Parkinson's disease", "Chronic constipation"],
                     v=dict(t=36.6, o2=97, p=72, rr=16, bp=(128, 74))),
    # ---- added with vitals
    "DEMO-023": dict(scenario="stable", sex="M", meal=(75, 100), mob="a walker", activity="chair exercises",
                     conditions=["Stroke (2023), left-sided weakness", "Hypertension", "Atrial fibrillation"],
                     v=dict(t=36.5, o2=96, p=78, rr=18, bp=(136, 80))),
    "DEMO-024": dict(scenario="stable_copd", sex="M", meal=(75, 100), mob="a walker", activity="the coffee group", copd=True,
                     conditions=["COPD (severe), oxygen at night", "Heart failure", "Osteoarthritis"],
                     v=dict(t=36.6, o2=91, p=84, rr=20, bp=(124, 72))),
    "DEMO-025": dict(scenario="fever_decline", sex="F", meal=(80, 100), mob="a walker", activity="the music program",
                     conditions=["Alzheimer's dementia (moderate)", "Hypertension", "Recurrent UTIs"],
                     v=dict(t=36.2, o2=96, p=72, rr=18, bp=(128, 76))),
    "DEMO-026": dict(scenario="respiratory_urgent", sex="M", meal=(80, 100), mob="a cane", activity="bingo",
                     conditions=["Hypertension", "Former smoker", "Osteoarthritis"],
                     v=dict(t=36.6, o2=96, p=76, rr=18, bp=(134, 78))),
    "DEMO-027": dict(scenario="isolated_vital", sex="F", meal=(80, 100), mob="a cane", activity="the music program",
                     conditions=["Osteoarthritis", "Generalized anxiety", "Hypertension"],
                     v=dict(t=36.6, o2=97, p=74, rr=16, bp=(132, 76))),
    "DEMO-028": dict(scenario="stable_low_bp", sex="F", meal=(75, 100), mob="standby assist", activity="bingo",
                     conditions=["Orthostatic hypotension", "Depression", "Osteoporosis"],
                     v=dict(t=36.5, o2=97, p=70, rr=16, bp=(102, 62))),
    "DEMO-029": dict(scenario="short_history", sex="M", meal=(75, 100), mob="a walker", activity="chair exercises",
                     start=date(2026, 10, 13), baseline=(date(2026, 10, 13), date(2026, 10, 13)),
                     conditions=["Lewy body dementia", "Hypertension"],
                     v=dict(t=36.6, o2=96, p=72, rr=18, bp=(138, 82))),
    "DEMO-030": dict(scenario="confusion_fever", sex="M", meal=(80, 100), mob="standby assist", activity="the coffee group",
                     conditions=["Type 2 diabetes", "Benign prostatic hyperplasia", "Hypertension"],
                     v=dict(t=36.5, o2=96, p=70, rr=16, bp=(136, 78))),
}

# ---------------------------------------------------------------- phrasing
# Written the way PSWs and nurses actually chart: shorthand (B/F, amb, DR, SBA, w/, BM x1,
# c/o, A&Ox3), fractions, missing capitals and periods, the odd typo. The meaning of every
# note is the same as before, so each resident's story (and the eval) is unchanged.
BUCKETS = [100, 90, 80, 75, 70, 60, 50, 40, 30, 25]
MEAL_NAMES = {
    "breakfast": ["breakfast", "bkfst", "B/F", "brkfst", "bfast", "b/f"],
    "lunch": ["lunch", "lunch", "Lunch"],
    "dinner": ["supper", "dinner", "supper"],
}
MOB_SHORT = {"a walker": "walker", "a cane": "cane", "standby assist": "SBA"}


def meal_phrase(pct, meal, pr):
    his = "her" if pr == "she" else "his"
    m = rng.choice(MEAL_NAMES[meal])
    if pct == 100:
        opts = [f"Ate all {m}.", f"{m} 100%.", f"ate 100% of {m}", f"finished {his} {m}", f"{m} - ate all."]
    elif pct == 90:
        opts = [f"ate almost all {m}", f"{m} 90%", f"Ate well @ {m}.", f"good appetite @ {m}"]
    elif pct in (80, 75):
        opts = [f"ate ~3/4 {m}", f"{m} {pct}%", f"Ate most of {m}.", f"{m} approx {pct}%"]
    elif pct in (70, 60):
        opts = [f"ate ~2/3 {m}", f"{m} {pct}%.", f"ate fair amt of {m}"]
    elif pct == 50:
        opts = [f"ate ~1/2 {m}", f"{m} 50%", f"Ate half {his} {m}."]
    else:
        opts = [f"ate ~{pct}% {m}", f"poor intake @ {m}", f"only few bites of {m}"]
    return rng.choice(opts)


ENERGY_OK = [
    "alert + chatty during am activities",
    "Bright, engaged this am.",
    "in good spirits, chatting w/ tablemates",
    "awake/alert for am care",
    "pleasant, A&Ox3",
]
NIGHT_OK = [
    "slept well overnight",
    "Up x1 to BR, settled back to sleep.",
    "repo'd @0200, slept between checks",
    "incont of urine x1, brief changed, settled back to sleep",
    "Slept well. checked q2h",
]
FLUIDS_OK = [
    "drank 2 cups juice + water",
    "good fluid intake",
    "fluids ~250ml",
    "finished tea + glass of water",
    "drinking well, fluids encouraged",
]
URINE_OK = [
    "toileted w/ assist, voided",
    "voided x2 this shift",
    "continent of urine, toileted before meal",
    "voiding qs",
]
BOWEL_OK = [
    "BM this am, formed",
    "BM x1 - normal",
    "small formed BM",
    "had a BM, type 4",
]
SOCIAL_OK = [
    "chatted w/ tablemates",
    "visited w/ family in lounge",
    "sat w/ friends in the lounge",
]
ORIENTED_OK = [
    "oriented, knew day of week",
    "A&Ox3",
    "following conversation well",
]
COPD_USUAL = [  # a chronic cough that is this resident's normal
    "productive cough, usual for him", "on O2 2L overnight per order", "occasional cough, at his baseline",
]
NURSE_EXTRA = [  # what registered staff tack on
    "VSS.", "No acute distress.", "Will cont to monitor.", "Meds taken w/o difficulty.", "Skin intact.",
]
NEGATIONS = [
    "Denies SOB.",
    "Denies pain.",
    "No s/s of fatigue today.",
    "No difficulty walking.",
    "No c/o pain.",
    "Not confused, oriented to place.",
    "No diarrhea.",
    "nil c/o pain",
]
# Typos only in words that carry no finding, so a slip never hides (or invents) a change.
TYPOS = {"dining": "dinning", "toileted": "toiletted", "family": "famliy", "settled": "setled",
         "chatting": "chating", "engaged": "engaed", "glass": "glas"}


def mob_ok(mob):
    m = MOB_SHORT.get(mob, mob)
    return rng.choice([
        f"amb to DR w/ {m}",
        f"Ambulated w/ {m}, steady.",
        f"walked back to room w/ {m}",
        f"amb w/ {m} - steady gait",
    ])


def scuff(text):
    """Make a generated note look hand-typed: lowercase starts, missing or extra
    punctuation, the odd typo. Only ever joins sentences with commas (a clause break),
    so a 'no' or 'denies' never reaches into the next sentence."""
    parts = [x.strip().rstrip(".") for x in text.split(". ") if x.strip()]
    sep = rng.choice([". ", ". ", ", ", ". ", "; "])
    out = sep.join(parts)
    if rng.random() < 0.18 and out[:3].lower() in ("ate", "amb", "sle", "up ", "dri"):
        out = rng.choice(["res ", "Res ", "pt ", "Resident "]) + out[0].lower() + out[1:]
    if rng.random() < 0.55:
        out = out[0].lower() + out[1:]
    elif rng.random() < 0.3:
        out = out[0].upper() + out[1:]
    if rng.random() < 0.5 and not out.endswith("."):
        out += "."
    if rng.random() < 0.15:
        for good, bad in TYPOS.items():
            if good in out:
                out = out.replace(good, bad, 1)
                break
    if rng.random() < 0.08:
        out = out.replace(" ", "  ", 1)
    return out


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

    def add(ts, parts, role=None):
        role = role or ("nurse" if rng.random() < 0.2 else "PSW")
        parts = [x.strip().rstrip(".") for x in parts]
        if role == "nurse" and rng.random() < 0.6:
            parts.append(rng.choice(NURSE_EXTRA).rstrip("."))
        notes.append(dict(resident_id=rid, recorded_at=ts, author_role=role,
                          note_text=scuff(". ".join(parts) + ".")))

    parts = [meal_phrase(normal_pct(p), "breakfast", pr)]
    if rng.random() < 0.4:
        parts.append(rng.choice(FLUIDS_OK))
    if rng.random() < 0.5:
        parts.append(rng.choice(ENERGY_OK))
    if rng.random() < 0.1:
        parts.append(rng.choice(ORIENTED_OK))
    if rng.random() < 0.35:
        parts.append(mob_ok(p["mob"]))
    if p.get("copd") and rng.random() < 0.35:
        parts.append(rng.choice(COPD_USUAL))
    add(stamp(d, 7, 9), parts)

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
            add(stamp(d, 12, 13), parts)
        elif slot == "dinner":
            parts = [meal_phrase(normal_pct(p), "dinner", pr)]
            if rng.random() < 0.25:
                parts.append(rng.choice(SOCIAL_OK))
            if rng.random() < 0.35:
                act = p["activity"].removeprefix("the ")
                parts.append(rng.choice([f"joined {act} after supper", f"Attended {act} this eve.", f"went to {act} after dinner"]))
            add(stamp(d, 18, 20), parts)
        else:
            add(stamp(d, 2, 5), [rng.choice(NIGHT_OK)], role="PSW")

    # Bowel movement roughly every 1-2 days, unless the scenario stops them.
    no_bm_from = p.get("no_bm_from")
    if rng.random() < 0.55 and not (no_bm_from and d >= no_bm_from):
        target = rng.choice([x for x in notes if int(x["recorded_at"][11:13]) >= 6])
        target["note_text"] = target["note_text"].rstrip(".") + rng.choice([". ", ", ", ". "]) + rng.choice(BOWEL_OK)
    return notes


# ------------------------------------------------- scripted recent windows
def n(rid, ts, role, text):
    return dict(resident_id=rid, recorded_at=ts, author_role=role, note_text=text)


SCRIPTED = {
    "DEMO-014": [  # planted decline: eating, drinking, energy, mobility, urine
        n("DEMO-014", "2026-10-14T08:15:00", "PSW", "ate ~1/2 bkfst. seemed more tired than usual during am activities"),
        n("DEMO-014", "2026-10-14T12:35:00", "PSW", "Lunch 60%. amb to DR w/ SBA"),
        n("DEMO-014", "2026-10-14T18:20:00", "PSW", "ate most of supper, asked to go to bed early."),
        n("DEMO-014", "2026-10-15T08:40:00", "PSW", "B/F 50%. quiet this am"),
        n("DEMO-014", "2026-10-15T12:30:00", "nurse", "Intake down - ate less than usual @ lunch. Drinking less than usual, left most of her juice. "
                                                      "Dozed in w/c after lunch which is unusual for her. Encouraged fluids, will monitor."),
        n("DEMO-014", "2026-10-16T08:20:00", "PSW", "bkfst ~40%, tired, needed prompting to finish"),
        n("DEMO-014", "2026-10-16T12:40:00", "nurse", "Lunch approx 40%. Needed hands on assist amb to DR (usually SBA only). Declined bingo this pm."),
        n("DEMO-014", "2026-10-16T19:00:00", "PSW", "poor intake @ supper, few bites only. needed hands on help back to room. voided x1 only this shift, urine dark"),
        n("DEMO-014", "2026-10-17T08:30:00", "PSW", "ate ~1/4 b/f. drank approx 1/3 of am fluids. v. sleepy during am care, hands on assist w/ amb"),
    ],
    "DEMO-019": [  # planted decline: eating, energy
        n("DEMO-019", "2026-10-14T08:30:00", "PSW", "B/F ~60%, amb to DR w/ SBA"),
        n("DEMO-019", "2026-10-14T12:20:00", "PSW", "ate 1/2 lunch. seemed tired, rested in room after"),
        n("DEMO-019", "2026-10-15T08:10:00", "PSW", "poor intake @ bkfst. drowsy during am care"),
        n("DEMO-019", "2026-10-15T12:45:00", "nurse", "Lunch approx 40%. Slept through most of the afternoon. Amb w/ SBA as per usual. VSS."),
        n("DEMO-019", "2026-10-16T08:35:00", "PSW", "ate abt half of bkfst, more tired than usual"),
        n("DEMO-019", "2026-10-16T18:30:00", "PSW", "supper 50%. declined bingo which he usually attends"),
        n("DEMO-019", "2026-10-17T08:25:00", "PSW", "bkfst 40%. sleepy but amb to DR w/ SBA"),
    ],
    "DEMO-015": [  # only ruled-out symptoms
        n("DEMO-015", "2026-10-14T08:20:00", "nurse", "Denies SOB. Ate well."),
        n("DEMO-015", "2026-10-14T12:30:00", "PSW", "lunch - ate most. amb to DR w/ walker"),
        n("DEMO-015", "2026-10-15T08:45:00", "PSW", "not tired today, joined exercise class. ate all bkfst"),
        n("DEMO-015", "2026-10-15T18:15:00", "PSW", "supper 90%. no diarrhea, no c/o pain"),
        n("DEMO-015", "2026-10-16T12:25:00", "PSW", "No difficulty walking, didn't need extra help to DR. Ate all lunch."),
        n("DEMO-015", "2026-10-16T19:10:00", "PSW", "supper 3/4. daughter visited"),
        n("DEMO-015", "2026-10-17T08:10:00", "nurse", "Denies pain/fatigue. Not confused, A&Ox3. B/F 90%."),
        n("DEMO-015", "2026-10-17T12:35:00", "PSW", "ate most of lunch"),
    ],
    "DEMO-017": [  # a fall: urgent at once
        n("DEMO-017", "2026-10-14T08:25:00", "PSW", "ate all bkfst, amb to DR w/ walker"),
        n("DEMO-017", "2026-10-14T12:40:00", "PSW", "lunch 80%"),
        n("DEMO-017", "2026-10-15T08:05:00", "PSW", "Ate most of b/f. alert + chatty during am activities"),
        n("DEMO-017", "2026-10-15T18:30:00", "PSW", "supper 90%, joined coffee group after"),
        n("DEMO-017", "2026-10-16T03:10:00", "nurse", "Unwitnessed fall - res found on floor beside bed @0300. Unable to WB on R leg, "
                                                      "grimacing w/ ROM to R hip. RN assessed, NP notified. Family aware."),
        n("DEMO-017", "2026-10-16T08:30:00", "PSW", "stayed in bed for bkfst per nurse. ate ~1/2"),
        n("DEMO-017", "2026-10-16T11:15:00", "nurse", "Transferred to ED via EMS for assessment of R hip. Son notified."),
    ],
    "DEMO-022": [  # no BM, eating less, tummy discomfort
        n("DEMO-022", "2026-10-14T08:30:00", "PSW", "B/F 75%. no BM again today"),
        n("DEMO-022", "2026-10-14T12:40:00", "PSW", "ate most of lunch, good fluid intake"),
        n("DEMO-022", "2026-10-15T08:20:00", "PSW", "bkfst ~60%. no BM since 10/12"),
        n("DEMO-022", "2026-10-15T18:30:00", "PSW", "ate ~1/2 supper. said her stomach feels full"),
        n("DEMO-022", "2026-10-16T08:40:00", "nurse", "No BM x4 days. Holding her stomach when standing, abd firm. B/F 50%. NP notified, PRN lax given."),
        n("DEMO-022", "2026-10-16T12:30:00", "PSW", "poor intake @ lunch. drank 1 cup only"),
        n("DEMO-022", "2026-10-17T08:15:00", "PSW", "No BM x5d. few bites of bkfst. declined coffee group"),
    ],
    "DEMO-018": [  # one tired morning, with a reason
        n("DEMO-018", "2026-10-15T08:30:00", "PSW", "ate all bkfst. tired this am after restless night, perked up by lunch"),
    ],
    "DEMO-021": [  # one small lunch, with a reason
        n("DEMO-021", "2026-10-15T12:30:00", "PSW", "lunch ~30% - said he had a big bkfst + wasn't hungry. amb w/ cane, cheerful"),
    ],
    "DEMO-016": [  # new admission
        n("DEMO-016", "2026-10-16T12:30:00", "PSW", "ate ~60% lunch. still settling in, asking for her daughter"),
    ],
    "DEMO-025": [  # the pitch example: sleepier, eating and drinking less, 37.5 against her usual 36.2
        n("DEMO-025", "2026-10-14T08:20:00", "PSW", "B/F 75%. alert + chatty during am care"),
        n("DEMO-025", "2026-10-14T12:40:00", "PSW", "lunch ~3/4, amb to DR w/ walker"),
        n("DEMO-025", "2026-10-15T08:35:00", "PSW", "ate ~1/2 bkfst. seemed more tired than usual"),
        n("DEMO-025", "2026-10-15T18:10:00", "PSW", "supper 50%, asked to go to bed early"),
        n("DEMO-025", "2026-10-16T08:30:00", "nurse", "Sleepier than usual this am, dozing in w/c. B/F ~40%. T 37.5 (usual 36.2), "
                                                      "encouraged fluids. Will recheck."),
        n("DEMO-025", "2026-10-16T12:35:00", "PSW", "poor intake @ lunch. drinking less than usual, left most of her tea"),
        n("DEMO-025", "2026-10-17T08:25:00", "nurse", "Drowsy, needed prompting w/ am care. ate ~1/4 b/f, drank ~1/3 of am fluids. "
                                                      "T 37.6, P 94. NP notified."),
    ],
    "DEMO-026": [  # oxygen falling over three days: urgent on the vitals alone
        n("DEMO-026", "2026-10-14T08:30:00", "PSW", "ate all bkfst, amb to DR w/ cane"),
        n("DEMO-026", "2026-10-14T18:20:00", "PSW", "supper 90%. coughing a bit after supper"),
        n("DEMO-026", "2026-10-15T08:45:00", "PSW", "B/F 75%. coughing more this am"),
        n("DEMO-026", "2026-10-15T13:00:00", "nurse", "Productive cough, sputum yellow. SpO2 93% RA, RR 22. Chest sounds coarse per RN. "
                                                      "Will monitor, encourage fluids."),
        n("DEMO-026", "2026-10-16T08:40:00", "PSW", "ate ~1/2 bkfst, coughing, breathing faster w/ am care"),
        n("DEMO-026", "2026-10-16T15:30:00", "nurse", "SpO2 91% RA, RR 25. Tired after walking to DR. NP aware, vitals q4h."),
        n("DEMO-026", "2026-10-17T07:55:00", "nurse", "SpO2 88% RA, RR 28, P 104, T 37.6. Using accessory muscles. "
                                                      "NP notified, O2 2L applied per order."),
    ],
    "DEMO-027": [  # one warm reading, normal on recheck
        n("DEMO-027", "2026-10-15T15:10:00", "nurse", "Felt warm after sitting by the heater, T 37.6. Rechecked 1h later T 36.7. "
                                                      "No other concerns, ate well @ lunch."),
    ],
    "DEMO-029": [  # new admission
        n("DEMO-029", "2026-10-16T12:20:00", "PSW", "lunch ~3/4. new admission, settling in well, wife visited"),
    ],
    "DEMO-030": [  # fever with new confusion
        n("DEMO-030", "2026-10-14T08:15:00", "PSW", "B/F 90%. pleasant, A&Ox3"),
        n("DEMO-030", "2026-10-14T18:40:00", "PSW", "supper ~3/4. joined coffee group"),
        n("DEMO-030", "2026-10-15T08:30:00", "PSW", "ate ~2/3 bkfst. seemed confused this am, asked what day it was x2"),
        n("DEMO-030", "2026-10-15T19:10:00", "PSW", "supper 50%. agitated in the evening, trying to leave the unit"),
        n("DEMO-030", "2026-10-16T08:40:00", "nurse", "New confusion - not oriented to place. T 37.9, P 104. Drinking less. "
                                                      "NP notified."),
        n("DEMO-030", "2026-10-16T15:10:00", "PSW", "disoriented, looking for his wife. drank 1 cup only"),
        n("DEMO-030", "2026-10-17T08:20:00", "nurse", "Remains confused, T 37.4, P 98. ate ~1/2 b/f. Encouraging fluids."),
    ],
}
# Residents whose whole recent window is scripted (others get generated notes plus their scripted ones).
FULLY_SCRIPTED = {"DEMO-014", "DEMO-019", "DEMO-015", "DEMO-017", "DEMO-022", "DEMO-025", "DEMO-026", "DEMO-030"}
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
                day_notes[-1]["note_text"] = rng.choice(NEGATIONS).rstrip(".") + ". " + day_notes[-1]["note_text"]
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
                         baseline_end=b1.isoformat(), conditions=p["conditions"], scenario=p["scenario"]))
    return rows


# ---------------------------------------------------------------- vitals
# Taken by registered staff about every other day (sparse, like the notes: not every shift),
# more often once someone is worried. Each resident varies a little around their own usual.
# A separate random stream, so adding vitals doesn't change any note.
vrng = random.Random(1914)
VITALS_DAILY = 0.5
SCRIPTED_VITALS = {
    "DEMO-014": [("2026-10-14T09:10:00", dict(t=36.4, o2=96, p=74)),
                 ("2026-10-15T09:00:00", dict(t=36.9, o2=96, p=84, rr=18, bp=(124, 72))),
                 ("2026-10-16T09:20:00", dict(t=37.4, o2=95, p=88, rr=20, bp=(118, 70))),
                 ("2026-10-17T09:05:00", dict(t=37.5, o2=95, p=92, rr=20, bp=(116, 68)))],
    "DEMO-017": [("2026-10-16T03:20:00", dict(t=36.8, o2=96, p=106, rr=20, bp=(154, 88))),   # after the fall
                 ("2026-10-16T08:45:00", dict(t=36.7, o2=96, p=98, bp=(146, 84)))],
    "DEMO-025": [("2026-10-14T09:15:00", dict(t=36.4, o2=96, p=74, rr=18, bp=(126, 74))),
                 ("2026-10-15T09:00:00", dict(t=36.9, o2=96, p=80)),
                 ("2026-10-16T08:25:00", dict(t=37.5, o2=95, p=90, rr=20, bp=(122, 72))),
                 ("2026-10-16T16:00:00", dict(t=37.4, o2=95, p=88)),
                 ("2026-10-17T08:20:00", dict(t=37.6, o2=95, p=94, rr=20, bp=(118, 70)))],
    "DEMO-026": [("2026-10-14T09:00:00", dict(t=36.6, o2=95, p=78, rr=20, bp=(132, 78))),
                 ("2026-10-15T12:55:00", dict(t=37.0, o2=93, p=84, rr=22, bp=(130, 76))),
                 ("2026-10-16T08:35:00", dict(t=37.1, o2=92, p=92, rr=24)),
                 ("2026-10-16T15:25:00", dict(t=37.3, o2=91, p=96, rr=25, bp=(128, 76))),
                 ("2026-10-17T07:50:00", dict(t=37.6, o2=88, p=104, rr=28, bp=(126, 74)))],
    "DEMO-027": [("2026-10-15T14:05:00", dict(t=37.6)),                                     # by the heater
                 ("2026-10-15T15:05:00", dict(t=36.7, o2=97, p=76))],                       # recheck
    "DEMO-030": [("2026-10-14T09:10:00", dict(t=36.6, o2=96, p=72, rr=16, bp=(134, 78))),
                 ("2026-10-15T09:00:00", dict(t=37.1, o2=96, p=84)),
                 ("2026-10-16T08:35:00", dict(t=37.9, o2=95, p=104, rr=20, bp=(128, 74))),
                 ("2026-10-16T15:00:00", dict(t=37.6, p=96)),
                 ("2026-10-17T08:15:00", dict(t=37.4, o2=96, p=98, rr=18, bp=(130, 76)))],
}
VITALS_SCRIPTED_RECENT = {"DEMO-014", "DEMO-025", "DEMO-026", "DEMO-030"}  # whole recent window scripted


def vital_row(rid, ts, v):
    bp = v.get("bp") or (None, None)
    return dict(resident_id=rid, recorded_at=ts, temp_c=v.get("t"), spo2=v.get("o2"), pulse=v.get("p"),
                resp_rate=v.get("rr"), bp_systolic=bp[0], bp_diastolic=bp[1], author_role="nurse")


def usual_reading(u):
    """One routine set around the resident's usual. Sometimes only temp, SpO2 and pulse."""
    t = round(min(max(vrng.gauss(u["t"], 0.15), u["t"] - 0.4), u["t"] + 0.4), 1)
    v = dict(t=t, o2=min(100, u["o2"] + vrng.choice([-1, 0, 0, 1])), p=u["p"] + vrng.randint(-6, 6))
    if vrng.random() < 0.7:
        v.update(rr=u["rr"] + vrng.choice([-2, 0, 0, 2]),
                 bp=(u["bp"][0] + vrng.randint(-8, 8), u["bp"][1] + vrng.randint(-5, 5)))
    return v


def build_vitals():
    out = []
    for rid, p in PROFILES.items():
        d = p.get("start", HISTORY_START)
        while d <= LAST_DAY:
            if not (rid in VITALS_SCRIPTED_RECENT and d >= RECENT_START) and vrng.random() < VITALS_DAILY:
                h0, h1 = vrng.choice([(8, 10), (8, 10), (14, 16)])
                minute = vrng.randrange(h0 * 60, h1 * 60)
                minute -= minute % 5
                ts = datetime(d.year, d.month, d.day, minute // 60, minute % 60).isoformat()
                out.append(vital_row(rid, ts, usual_reading(p["v"])))
            d += timedelta(days=1)
        out.extend(vital_row(rid, ts, v) for ts, v in SCRIPTED_VITALS.get(rid, []))
    out.sort(key=lambda x: (x["resident_id"], x["recorded_at"]))
    return out


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
                       categories=["nutrition", "fluids", "energy", "mobility", "toileting.urine", "temperature"],
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
    dict(resident_id="DEMO-023", scenario="stable", expected=dict(alert_created=False, reason="normal variation within usual range")),
    dict(resident_id="DEMO-024", scenario="stable_copd",
         expected=dict(alert_created=False, reason="SpO2 of 90-92% and a daily cough are this resident's usual")),
    dict(resident_id="DEMO-025", scenario="fever_decline",
         expected=dict(alert_created=True, categories=["temperature", "energy", "nutrition", "fluids"],
                       reason="37.5 C is a fever for her: more than 1.1 C above her usual 36.2 (IDSA)")),
    dict(resident_id="DEMO-026", scenario="respiratory_urgent",
         expected=dict(alert_created=True, urgent=True, categories=["oxygen", "breathing_rate"],
                       reason="SpO2 down from a usual 96% to 88% with fast breathing")),
    dict(resident_id="DEMO-027", scenario="isolated_vital",
         expected=dict(alert_created=False, reason="one warm reading, normal on recheck")),
    dict(resident_id="DEMO-028", scenario="stable_low_bp",
         expected=dict(alert_created=False, reason="systolic around 100 is this resident's usual")),
    dict(resident_id="DEMO-029", scenario="short_history",
         expected=dict(alert_created=False, baseline_limited=True, reason="fewer than 7 days of history")),
    dict(resident_id="DEMO-030", scenario="confusion_fever",
         expected=dict(alert_created=True, categories=["confusion", "temperature"],
                       reason="fever with new confusion (Loeb)")),
]


# ---------------------------------------------------------------- checks
def check(residents, notes, cases, vitals):
    ids = {r["id"] for r in residents}
    assert all(x["resident_id"] in ids for x in notes)
    assert all(x["resident_id"] in ids for x in vitals)
    assert len(residents) == 20
    for rid, p in PROFILES.items():  # routine readings stay inside the resident's own normal
        u, scripted = p["v"], {ts for ts, _ in SCRIPTED_VITALS.get(rid, [])}
        for x in vitals:
            if x["resident_id"] != rid or x["recorded_at"] in scripted:
                continue
            assert abs(x["temp_c"] - u["t"]) <= 0.4 and abs(x["spo2"] - u["o2"]) <= 1, x
            assert x["pulse"] <= 100 and (x["resp_rate"] or 0) < 25, x
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
    low = [x for x in notes if x["resident_id"] == "DEMO-021" and any(s in x["note_text"] for s in (
        "30%", "40%", "25%", "poor intake", "few bites", "1/2", "half"))]
    assert len(low) == 1, low
    # constipation resident: no BM recorded from Oct 12 onward
    assert not [x for x in notes if x["resident_id"] == "DEMO-022" and x["recorded_at"] >= "2026-10-12"
                and any(b in x["note_text"] for b in BOWEL_OK)]


# ---------------------------------------------------------------- people (people.json)
PEOPLE = json.loads((Path(__file__).parent / "people.json").read_text(encoding="utf-8"))


def name_people(residents, notes, evals, vitals):
    """Swap the internal DEMO-0xx keys for unit IDs + names, and give each note and each set
    of vitals one of the unit's nurses (random, but the same every run)."""
    ids = {r["old_id"]: r for r in PEOPLE["residents"]}
    nurses = [n["name"] for n in PEOPLE["nurses"]]
    pick, vpick = random.Random(2026), random.Random(2027)
    residents = [{**r, "id": ids[r["id"]]["id"], "display_name": ids[r["id"]]["name"]} for r in residents]
    notes = [{**n, "resident_id": ids[n["resident_id"]]["id"], "author_name": pick.choice(nurses)} for n in notes]
    vitals = [{**v, "resident_id": ids[v["resident_id"]]["id"], "author_name": vpick.choice(nurses)} for v in vitals]
    evals = [{**e, "resident_id": ids[e["resident_id"]]["id"]} for e in evals]
    return residents, notes, evals, vitals


def main():
    OUT.mkdir(exist_ok=True)
    residents, notes, vitals = build_residents(), build_notes(), build_vitals()
    check(residents, notes, CASES, vitals)
    residents, notes, evals, vitals = name_people(residents, notes, EVAL, vitals)
    for name, data in [("residents", residents), ("notes", notes), ("vitals", vitals), ("cases", CASES),
                       ("eval_scenarios", evals)]:
        (OUT / f"{name}.json").write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n")
    print(f"{len(residents)} residents, {len(notes)} notes, {len(vitals)} vitals, {len(CASES)} cases, "
          f"{len(EVAL)} eval scenarios")


if __name__ == "__main__":
    main()
