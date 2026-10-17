"""Generate CareSignal seed files: residents, notes, cases, eval scenarios.

Deterministic (fixed random seed). Run: python generate_seed.py
Writes seed/residents.json, seed/notes.json, seed/cases.json, seed/eval_scenarios.json
All data is fictional.
"""
import json
import random
from datetime import date, datetime, timedelta
from pathlib import Path

rng = random.Random(42)
OUT = Path(__file__).parent / "seed"

HISTORY_START = date(2026, 9, 20)
BASELINE_END = date(2026, 10, 10)
RECENT_START = date(2026, 10, 14)
LAST_DAY = date(2026, 10, 17)
CATEGORIES = ("nutrition", "energy", "mobility")

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
]
NEGATIONS = [
    "Denies shortness of breath.",
    "Denies pain.",
    "No signs of fatigue today.",
    "No difficulty walking.",
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
    if rng.random() < 0.5:
        parts.append(rng.choice(ENERGY_OK))
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
                parts.append(mob_ok(p["mob"]))
            add(stamp(d, 12, 13), " ".join(parts))
        elif slot == "dinner":
            parts = [meal_phrase(normal_pct(p), "dinner", pr)]
            if rng.random() < 0.35:
                parts.append(f"Joined {p['activity']} after dinner.")
            add(stamp(d, 18, 20), " ".join(parts))
        else:
            add(stamp(d, 2, 5), rng.choice(NIGHT_OK), role="PSW")
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
        n("DEMO-014", "2026-10-15T12:30:00", "nurse", "Ate less than usual at lunch. Dozed in chair after lunch, which is unusual for her."),
        n("DEMO-014", "2026-10-16T08:20:00", "PSW", "Ate about 40% of breakfast. Tired, needed prompting to finish."),
        n("DEMO-014", "2026-10-16T12:40:00", "nurse", "Ate about 40% of lunch. Needed hands-on help walking to dining room, usually only standby. Declined afternoon bingo."),
        n("DEMO-014", "2026-10-16T19:00:00", "PSW", "Ate poorly at dinner, a few bites only. Needed hands-on help to walk back to room."),
        n("DEMO-014", "2026-10-17T08:30:00", "PSW", "Ate about a quarter of breakfast. Very sleepy during morning care. Needed hands-on assist walking."),
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
        n("DEMO-015", "2026-10-15T18:15:00", "PSW", "Ate 90% of dinner."),
        n("DEMO-015", "2026-10-16T12:25:00", "PSW", "No difficulty walking, did not need extra help to the dining room. Ate all of lunch."),
        n("DEMO-015", "2026-10-16T19:10:00", "PSW", "Ate 75% of dinner. Daughter visited."),
        n("DEMO-015", "2026-10-17T08:10:00", "nurse", "Denies pain or fatigue. Ate 90% of breakfast."),
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
FULLY_SCRIPTED = {"DEMO-014", "DEMO-019", "DEMO-015", "DEMO-017"}
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
CAT = {"N": "nutrition", "E": "energy", "M": "mobility"}


def case(cid, summary, codes, timeline, days, outcome, limitation):
    direction = "improving" if codes.startswith("+") else "worsening"
    cats = [CAT[c] for c in codes.lstrip("+")]
    return dict(
        id=cid, case_summary=summary,
        observations=[dict(category=c, direction=direction) for c in cats],
        timeline=[dict(day=dy, category=CAT[c], note=t) for dy, c, t in timeline],
        duration_days=days, documented_outcome=outcome, limitations=limitation,
    )


CASES = [
    # ---- nutrition + energy + mobility, worsening (11)
    case("CASE-001", "Over four days, resident ate less, slept more during the day and needed more help transferring.", "NEM",
         [(1, "N", "Ate about half of breakfast and lunch"), (2, "E", "Dozed through morning activities"), (3, "M", "Needed one-person assist to transfer, usually independent")], 4,
         "Nurse assessment found a low-grade temperature; the NP diagnosed a respiratory infection treated in the home. Back to usual routine by day 10.",
         "No vital signs recorded before day 3."),
    case("CASE-002", "Gradual decline over six days in meal intake, alertness and walking.", "NEM",
         [(1, "N", "Ate about 60% of meals"), (3, "E", "Sleepy at lunch, needed prompting"), (5, "M", "Unsteady, required hands-on assist")], 6,
         "Bloodwork showed dehydration; a hydration plan was started and the resident recovered over one week.",
         "Fluid intake was not recorded on days 1 to 3."),
    case("CASE-003", "Rapid change over three days: poor intake, drowsiness and inability to walk to the dining room.", "NEM",
         [(1, "N", "Ate a few bites of breakfast"), (1, "E", "Very drowsy during morning care"), (2, "M", "Could not walk to dining room, used wheelchair")], 3,
         "Transferred to hospital on day 3 after a nurse found low oxygen saturation; admitted with pneumonia.",
         "Record does not include hospital discharge details."),
    case("CASE-004", "Over five days, resident ate less, seemed sedated in the mornings and was unsteady walking.", "NEM",
         [(1, "E", "Hard to wake for breakfast"), (2, "N", "Ate about 50% of meals"), (3, "M", "Unsteady on feet, needed standby to hands-on assist")], 5,
         "Medication review found a sedating medication started the week before; the dose was reduced and changes resolved within four days.",
         "Exact start date of the new medication is unclear."),
    case("CASE-005", "Over a week, resident ate less, withdrew from activities and walked less.", "NEM",
         [(1, "E", "Declined usual activity"), (3, "N", "Ate about 60% of meals"), (6, "M", "Preferred wheelchair over walking")], 7,
         "Assessed by the NP; no medical cause found. The team noted low mood, and the resident returned to usual pattern over two weeks after family visits and activity changes.",
         "No mood screening score documented."),
    case("CASE-006", "Resident ate less, was tired and needed more help walking over four days.", "NEM",
         [(1, "N", "Ate about half of lunch and dinner"), (2, "E", "Tired, napping more"), (4, "M", "Needed hands-on help walking")], 4,
         "Constipation identified on assessment (no bowel movement for five days); bowel routine adjusted and intake recovered.",
         "Bowel records incomplete for the prior week."),
    case("CASE-007", "Over five days, resident ate less at most meals, seemed unusually tired, and began needing more help walking.", "NEM",
         [(1, "N", "Ate about 60% of meals"), (2, "E", "More tired than usual"), (4, "M", "Needed extra assistance walking")], 5,
         "Care team requested a clinical assessment; a medical cause was identified and treated.",
         "Record does not state the resident's baseline mobility or any medication changes."),
    case("CASE-008", "Over five days, resident ate less, was tired and walked less, with new reports of knee pain.", "NEM",
         [(1, "M", "Reluctant to walk to dining room"), (2, "N", "Ate about 60% of meals"), (4, "E", "Rested in room most afternoons")], 5,
         "Urine culture negative; the NP attributed the changes to worsening arthritis pain. Pain plan adjusted and mobility improved partially.",
         "Pain scores not recorded until day 4."),
    case("CASE-009", "Over six days, resident ate less, was drowsy and needed help walking; two others on the unit had similar changes.", "NEM",
         [(1, "E", "Drowsy at breakfast"), (2, "N", "Ate about half of meals"), (3, "M", "Needed hands-on assist walking")], 6,
         "COVID-19 test positive on day 2; resident isolated and recovered in the home. Two other residents on the unit tested positive that week.",
         "Onset dates for the other residents are not recorded in this case."),
    case("CASE-010", "For three days resident ate less, was tired and unsteady after a room move.", "NEM",
         [(1, "E", "Tired after a poor night"), (1, "N", "Ate about 60% of breakfast"), (2, "M", "Slightly unsteady walking")], 3,
         "Changes resolved without treatment by day 5. Nurse noted a disrupted sleep schedule after the room move.",
         "Short follow-up; no clinical assessment documented."),
    case("CASE-011", "Over five days, resident ate less, slept more and stopped walking to meals.", "NEM",
         [(1, "N", "Ate about 40% of meals"), (2, "E", "Sleeping most of the day"), (4, "M", "Stayed in wheelchair for all transfers")], 5,
         "Resident declined further assessment in line with advance care wishes; comfort-focused care continued and family was updated.",
         "Cause of the change was not investigated."),
    # ---- nutrition + energy, worsening (9)
    case("CASE-012", "Resident ate less and seemed tired for two days. No mobility change recorded.", "NE",
         [(1, "N", "Ate about half of dinner"), (2, "E", "Tired during activities")], 2,
         "Symptoms resolved after a medication timing adjustment. No further concerns.",
         "Short observation window; no follow-up beyond day 4."),
    case("CASE-013", "Resident ate less and was drowsy before lunch for three days.", "NE",
         [(1, "E", "Drowsy before lunch"), (2, "N", "Ate about half of lunch")], 3,
         "Low blood sugar episodes found; diabetes medication adjusted.",
         "Blood glucose checked only once daily."),
    case("CASE-014", "Resident ate much less and was tired and irritable for two days.", "NE",
         [(1, "N", "Ate only soft parts of meals, about 40%"), (2, "E", "Tired and irritable")], 2,
         "Dental abscess found; dental visit arranged and intake recovered after treatment.",
         "Mouth not examined until day 2."),
    case("CASE-015", "Over four days, resident ate less and was very tired, with new aches.", "NE",
         [(1, "E", "Very tired, stayed in bed for breakfast"), (2, "N", "Ate about a quarter of meals")], 4,
         "Influenza confirmed by swab; antiviral started. Resident recovered over ten days.",
         "Vaccination status not recorded in this case."),
    case("CASE-016", "Resident ate less and seemed tired for five days.", "NE",
         [(1, "N", "Ate about 60% of meals"), (3, "E", "Tired during afternoon activities")], 5,
         "No cause found on assessment; appetite and energy returned without intervention by day 8.",
         "No weight recorded."),
    case("CASE-017", "Over three days, resident ate less and was lethargic.", "NE",
         [(1, "E", "Lethargic in the morning"), (2, "N", "Ate about half of meals")], 3,
         "Bloodwork showed low sodium; the NP adjusted a diuretic and the resident improved.",
         "Baseline bloodwork was more than six months old."),
    case("CASE-018", "Over six days, resident ate less and withdrew from usual activities after a roommate died.", "NE",
         [(1, "E", "Declined usual activities"), (2, "N", "Ate about 60% of meals")], 6,
         "Team identified grief; social work and chaplain visits followed and intake improved slowly.",
         "No standardized mood assessment completed."),
    case("CASE-019", "Resident ate less and seemed tired for two days, complaining of mouth soreness.", "NE",
         [(1, "N", "Ate about half of breakfast, chewing slowly"), (2, "E", "Tired after lunch")], 2,
         "A denture sore spot was found; the denture was adjusted and intake returned to normal within three days.",
         "The tiredness is not explained in the record."),
    case("CASE-020", "Over four days, resident ate less and was tired, then developed a fever.", "NE",
         [(1, "E", "More tired than usual"), (2, "N", "Ate about half of meals")], 4,
         "Urinary tract infection confirmed by culture alongside the new fever; antibiotics given.",
         "Urine sample collected on day 4, after symptoms had progressed."),
    # ---- nutrition + mobility, worsening (5)
    case("CASE-021", "Over four days, resident ate less and was reluctant to walk, guarding one hip.", "NM",
         [(1, "M", "Reluctant to walk, guarding left hip"), (2, "N", "Ate about 60% of meals")], 4,
         "Hip pain traced to an unreported fall; X-ray showed no fracture. Physiotherapy started.",
         "Date of the fall is unknown."),
    case("CASE-022", "Over six days, resident ate less and became short of breath walking short distances.", "NM",
         [(1, "M", "Stopped to rest walking to dining room"), (3, "N", "Ate about half of meals")], 6,
         "Worsening heart failure; the NP adjusted medications and swelling and walking improved.",
         "Daily weights missing on three days."),
    case("CASE-023", "Over three days, resident ate less and limped when walking.", "NM",
         [(1, "M", "Limping on right foot"), (2, "N", "Ate about 60% of lunch")], 3,
         "A painful foot wound was found during a bath; wound care started and walking improved as it healed.",
         "Skin check frequency not documented."),
    case("CASE-024", "Resident ate less and needed more help walking for five days.", "NM",
         [(1, "N", "Ate about 60% of meals"), (3, "M", "Needed hands-on assist with walker")], 5,
         "No clear cause found; the resident's damaged walker was replaced and intake returned to baseline.",
         "Unclear whether the two changes were related."),
    case("CASE-025", "Over a week, resident ate less, took longer at meals and shuffled more when walking.", "NM",
         [(1, "N", "Took over an hour to eat half of lunch"), (5, "M", "Shuffling gait, needed hands-on assist")], 7,
         "NP noted progression of Parkinson's disease; care plan updated to more assistance at meals and walking.",
         "Neurology follow-up not included."),
    # ---- energy + mobility, worsening (5)
    case("CASE-026", "Over three days, resident was drowsy and unsteady in the mornings.", "EM",
         [(1, "E", "Drowsy until mid-morning"), (2, "M", "Unsteady walking to breakfast")], 3,
         "Over-sedation after a new sleep medication; medication stopped and resident back to usual by day 5.",
         "Medication start date recorded only in pharmacy notes."),
    case("CASE-027", "Over four days, resident was tired and needed rests while walking.", "EM",
         [(1, "E", "Tired during activities"), (3, "M", "Needed rests walking to dining room")], 4,
         "Low hemoglobin found on bloodwork; the NP arranged further investigation and started iron.",
         "Investigation results are not in this record."),
    case("CASE-028", "For two days resident was tired and slightly unsteady after a late family outing.", "EM",
         [(1, "E", "Tired after late outing"), (1, "M", "Slightly unsteady in the evening")], 2,
         "Changes resolved after one day; attributed to the late-night outing.",
         "Single-shift observation only."),
    case("CASE-029", "Over five days, resident was drowsy and increasingly unsteady, then fell.", "EM",
         [(1, "E", "Drowsy after lunch"), (3, "M", "Needed hands-on assist walking"), (5, "M", "Fall with head strike")], 5,
         "Transferred to hospital on day 5 after a fall with head strike; returned to the home after two days.",
         "Hospital findings summarized only briefly."),
    case("CASE-030", "Over six days, resident was sluggish and slow walking.", "EM",
         [(1, "E", "Sluggish in the mornings"), (4, "M", "Walking much slower than usual")], 6,
         "Hypothyroidism found on bloodwork; thyroid medication adjusted with gradual improvement.",
         "No prior thyroid results for comparison."),
    # ---- nutrition only, worsening (5)
    case("CASE-031", "Resident ate less for three days after the menu changed.", "N",
         [(1, "N", "Left most of new menu items"), (2, "N", "Ate about half of meals")], 3,
         "Resident disliked the new menu items; the dietitian added preferred alternatives and intake recovered.",
         "Fluid intake not recorded."),
    case("CASE-032", "Over five days, resident ate less and coughed during meals.", "N",
         [(1, "N", "Coughing while eating, ate about half"), (4, "N", "Refused bread and meat")], 5,
         "Swallowing difficulty identified by a speech-language pathologist; diet texture changed.",
         "No choking events documented before the referral."),
    case("CASE-033", "Resident ate less for two days.", "N",
         [(1, "N", "Ate about 60% of meals"), (2, "N", "Ate about half of dinner")], 2,
         "Intake returned to normal on day 3; no cause recorded.",
         "No assessment documented."),
    case("CASE-034", "Over a week, resident ate less at most meals.", "N",
         [(1, "N", "Ate about 60% of meals"), (7, "N", "Still eating about 60%")], 7,
         "Weight loss of 3 kg over a month confirmed; the dietitian started supplements.",
         "Weights recorded monthly only."),
    case("CASE-035", "Over four days, resident ate less and reported nausea.", "N",
         [(1, "N", "Nauseated, ate about half of breakfast"), (3, "N", "Ate about 40% of meals")], 4,
         "Nausea attributed to a new antibiotic for a skin infection; resolved after the course ended.",
         "Antibiotic name not recorded in this case."),
    # ---- energy only, worsening (3)
    case("CASE-036", "Over three days, resident was tired during the day.", "E",
         [(1, "E", "Napping through morning activities"), (3, "E", "Still tired in the afternoon")], 3,
         "Sleep disrupted by a noisy roommate; a room change resolved the daytime tiredness.",
         "Night-shift notes are sparse."),
    case("CASE-037", "Over five days, resident withdrew from activities and seemed low in energy.", "E",
         [(1, "E", "Declined usual activities"), (5, "E", "Stayed in room most of the day")], 5,
         "Depression screening was positive; the physician started treatment and engagement improved over several weeks.",
         "Screening tool not named."),
    case("CASE-038", "Resident was tired for two days.", "E",
         [(1, "E", "Tired at breakfast"), (2, "E", "Rested after lunch")], 2,
         "Tiredness resolved by day 3; no cause found.",
         "No vital signs recorded."),
    # ---- mobility only, worsening (4)
    case("CASE-039", "Over four days, resident walked less and complained of knee pain.", "M",
         [(1, "M", "Knee pain when walking"), (3, "M", "Needed hands-on assist with walker")], 4,
         "Knee osteoarthritis flare; pain medication and physiotherapy improved walking.",
         "No pain score recorded before day 2."),
    case("CASE-040", "Resident was unsteady walking for two days after getting new shoes.", "M",
         [(1, "M", "Unsteady in new shoes"), (2, "M", "Near-fall in hallway")], 2,
         "New shoes were causing instability; the resident returned to old footwear and walking normalized.",
         "Single observer."),
    case("CASE-041", "Over six days, resident was dizzy and unsteady when standing.", "M",
         [(1, "M", "Dizzy on standing"), (4, "M", "Needed hands-on assist to stand")], 6,
         "Dizziness on standing confirmed; blood pressure medication reduced and falls risk lowered.",
         "Standing blood pressure checked only once."),
    case("CASE-042", "Over three days, resident was increasingly unsteady, then had an unwitnessed fall.", "M",
         [(1, "M", "Unsteady walking"), (3, "M", "Found on floor, unable to stand")], 3,
         "Transferred to hospital for a hip fracture after the unwitnessed fall on day 3.",
         "The earlier mobility change is not linked to the fall in the record."),
    # ---- improving only: no overlap with a worsening pattern (8)
    case("CASE-043", "Over five days, resident's appetite improved after dentures were relined.", "+N",
         [(1, "N", "Ate about 70% of meals"), (5, "N", "Ate all of most meals")], 5,
         "Intake stayed at baseline over the following month.",
         "No weight recorded after the change."),
    case("CASE-044", "Over a week of physiotherapy, resident needed less help walking.", "+M",
         [(1, "M", "Hands-on assist with walker"), (7, "M", "Walking with standby only")], 7,
         "Physiotherapy goals met; resident discharged from the program.",
         "Physiotherapy notes summarized, not attached."),
    case("CASE-045", "Over four days, resident became more alert after a sedating medication was stopped.", "+E",
         [(1, "E", "Drowsy in the mornings"), (4, "E", "Alert and joining activities")], 4,
         "Resident stayed alert; medication not restarted.",
         "Reason for the original medication not recorded."),
    case("CASE-046", "Over six days of recovery from influenza, resident ate more and had more energy.", "+NE",
         [(1, "N", "Ate about 60% of meals"), (3, "E", "Joined one activity"), (6, "N", "Back to eating most meals")], 6,
         "Resident returned to usual routine; no complications.",
         "Influenza onset is described in a separate record."),
    case("CASE-047", "Over three days with a new walker, resident walked more steadily.", "+M",
         [(1, "M", "Started using new walker"), (3, "M", "Walking steadily to all meals")], 3,
         "No falls in the following month.",
         "Short observation window."),
    case("CASE-048", "Over four days on a nutrition supplement, resident's intake improved.", "+N",
         [(1, "N", "Ate about 60% plus supplement"), (4, "N", "Ate about 80% of meals")], 4,
         "Dietitian continued the supplement; weight stable at the next monthly check.",
         "Intake before the supplement recorded for only two days."),
    case("CASE-049", "Over a week after returning from hospital, resident regained energy and walking.", "+EM",
         [(1, "E", "Tired, resting most of the day"), (3, "M", "Walking short distances with assist"), (7, "M", "Walking to dining room with standby")], 7,
         "Resident returned to pre-hospital level of function.",
         "Hospital stay details not included."),
    case("CASE-050", "Over five days as a foot wound healed, resident ate more and walked more.", "+NM",
         [(1, "M", "Walking short distances only"), (3, "N", "Ate most of meals"), (5, "M", "Walking to all meals")], 5,
         "Wound healed; resident back to usual mobility.",
         "Wound measurements not recorded."),
]

# ---------------------------------------------------------------- eval scenarios
EVAL = [
    dict(resident_id="DEMO-011", scenario="stable", expected=dict(alert_created=False, reason="normal variation within usual range")),
    dict(resident_id="DEMO-012", scenario="stable", expected=dict(alert_created=False, reason="normal variation within usual range")),
    dict(resident_id="DEMO-013", scenario="stable", expected=dict(alert_created=False, reason="normal variation within usual range")),
    dict(resident_id="DEMO-014", scenario="planted_decline",
         expected=dict(alert_created=True, categories=["nutrition", "energy", "mobility"], min_similar_cases=2)),
    dict(resident_id="DEMO-015", scenario="negation_test",
         expected=dict(alert_created=False, reason="negated symptoms only",
                       must_not_extract=[dict(category="energy", direction="worsening"),
                                         dict(category="mobility", direction="worsening")])),
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
]


# ---------------------------------------------------------------- checks
def check(residents, notes, cases):
    ids = {r["id"] for r in residents}
    assert all(x["resident_id"] in ids for x in notes)
    assert len(cases) == 50 and len({c["id"] for c in cases}) == 50
    assert {"CASE-007", "CASE-012"} <= {c["id"] for c in cases}
    for c in cases:
        cats = {o["category"] for o in c["observations"]}
        assert cats <= set(CATEGORIES) and 1 <= len(cats) <= 3
        assert 2 <= c["duration_days"] <= 7 and c["limitations"] and c["documented_outcome"]
        assert {t["category"] for t in c["timeline"]} == cats, c["id"]
        assert all(t["day"] <= c["duration_days"] for t in c["timeline"]), c["id"]
    for r in residents:
        own = [x for x in notes if x["resident_id"] == r["id"]]
        days = {x["recorded_at"][:10] for x in own}
        per_day = [sum(1 for x in own if x["recorded_at"][:10] == d) for d in days]
        assert max(per_day) <= 3 or r["id"] in FULLY_SCRIPTED, r["id"]
    # isolated-dip resident: exactly one meal below 60% in the whole record
    low = [x for x in notes if x["resident_id"] == "DEMO-021" and any(s in x["note_text"] for s in ("30%", "40%", "25%", "poorly", "few bites", "half"))]
    assert len(low) == 1, low


def main():
    OUT.mkdir(exist_ok=True)
    residents, notes = build_residents(), build_notes()
    check(residents, notes, CASES)
    for name, data in [("residents", residents), ("notes", notes), ("cases", CASES), ("eval_scenarios", EVAL)]:
        (OUT / f"{name}.json").write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n")
    print(f"{len(residents)} residents, {len(notes)} notes, {len(CASES)} cases, {len(EVAL)} eval scenarios")


if __name__ == "__main__":
    main()
