from datetime import timedelta
from statistics import mean, median

RECENT_DAYS = 4     # the last 4 days are "recent"; everything before is the baseline
MIN_BASELINE = 5    # fewer old numbers than this = "limited baseline"

# SETTING 1: every factor we watch, and how many recent WORSENING notes flag it.
NOTES_NEEDED = {
    "nutrition": 2,
    "fluids": 2,
    "sleep": 2,
    "pain": 2,
    "energy": 2,
    "mobility": 2,
    "confusion": 1,          # flagged on a single note
    "social": 2,
    "toileting_urine": 2,
    "toileting_bowel": 2,
    "toileting_other": 2,
}

# SETTING 2: factors measured as a percentage, and how far below usual counts as a drop.
DROP_NEEDED = {
    "nutrition": 20,         # meals: 20 percentage points below usual
    "fluids": 25,
}

# SETTING 3: serious phrases that skip everything and raise an urgent alert.
URGENT_PHRASES = [
    "head strike", "found on floor", "unable to stand", "low oxygen",
    "chest pain", "unresponsive", "difficulty breathing", "short of breath at rest",
    "severe pain", "not breathing", "seizure",
]


# ---------- small helpers ----------

def factor_of(obs):
    """Which factor is this observation about? Toileting is split into urine / bowel."""
    if obs["category"] == "toileting":
        subcategory = obs.get("subcategory")
        if subcategory:
            return "toileting_" + subcategory
        return "toileting_other"
    return obs["category"]


def split_old_and_recent(observations, as_of):
    """Skip negated/uncertain notes, then split the rest into (old, recent)."""
    cutoff = as_of - timedelta(days=RECENT_DAYS)
    old = []
    recent = []
    for obs in observations:
        if obs["assertion"] != "present":
            continue
        if obs["recorded_at"] < cutoff:
            old.append(obs)
        else:
            recent.append(obs)
    return old, recent


def notes_for(factor, observations):
    """Only the observations about one factor."""
    matching = []
    for obs in observations:
        if factor_of(obs) == factor:
            matching.append(obs)
    return matching


def numbers_in(observations):
    """The numeric values (like 85 for '85% of meal') from a list of observations."""
    values = []
    for obs in observations:
        if obs.get("numeric_value") is not None:
            values.append(obs["numeric_value"])
    return values


def make_finding(factor, message, evidence):
    ids = []
    first_seen = evidence[0]["recorded_at"]
    last_seen = evidence[0]["recorded_at"]
    for obs in evidence:
        ids.append(obs["id"])
        if obs["recorded_at"] < first_seen:
            first_seen = obs["recorded_at"]
        if obs["recorded_at"] > last_seen:
            last_seen = obs["recorded_at"]

    return {
        "factor": factor,
        "message": message,
        "evidence": ids,
        "first_seen": first_seen,
        "last_seen": last_seen,
    }


# ---------- step 1: baseline ----------

def compute_baseline(observations, as_of):
    """The resident's usual value for meals and fluids, from OLD notes only."""
    old, _ = split_old_and_recent(observations, as_of)

    baseline = {}
    for factor in DROP_NEEDED:
        values = numbers_in(notes_for(factor, old))

        if len(values) > 0:
            usual = median(values)
        else:
            usual = None

        baseline[factor] = {
            "usual": usual,
            "based_on": len(values),
            "limited": len(values) < MIN_BASELINE,
        }
    return baseline


# ---------- step 2: detection ----------

def check_numbers(factor, notes, baseline):
    """Did the recent percentage fall well below usual? Returns a finding or None."""
    if factor not in DROP_NEEDED:
        return None

    usual = baseline[factor]["usual"]
    recent_values = numbers_in(notes)
    if usual is None or len(recent_values) < 2:
        return None

    recent_average = mean(recent_values)
    drop = usual - recent_average
    if drop < DROP_NEEDED[factor]:
        return None

    evidence = []
    for obs in notes:
        if obs.get("numeric_value") is not None:
            evidence.append(obs)

    message = f"{factor} averaged {recent_average:.0f}% vs usual {usual:.0f}%"
    return make_finding(factor, message, evidence)


def check_worsening_notes(factor, notes):
    """Are there enough recent notes saying it got worse? Returns a finding or None."""
    worse = []
    for obs in notes:
        if obs["direction"] == "worsening":
            worse.append(obs)

    if len(worse) < NOTES_NEEDED[factor]:
        return None

    name = factor.replace("_", " ")
    message = f"{len(worse)} recent note(s) describe worsening {name}"
    return make_finding(factor, message, worse)


def detect_changes(observations, baseline, as_of):
    _, recent = split_old_and_recent(observations, as_of)

    findings = []
    for factor in NOTES_NEEDED:
        notes = notes_for(factor, recent)

        finding = check_numbers(factor, notes, baseline)
        if finding is None:
            finding = check_worsening_notes(factor, notes)

        if finding is not None:
            findings.append(finding)
    return findings


# ---------- step 3: urgent check ----------

def check_urgent(notes, as_of):
    """Look for serious phrases in recent raw notes. No pattern needed."""
    cutoff = as_of - timedelta(days=RECENT_DAYS)

    urgent = []
    for note in notes:
        if note["recorded_at"] < cutoff:
            continue

        text = note["note_text"].lower()
        found = []
        for phrase in URGENT_PHRASES:
            if phrase in text:
                found.append(phrase)

        if len(found) > 0:
            message = "Note mentions: " + ", ".join(found) + ". Follow facility escalation procedure."
            evidence = [{"id": note["id"], "recorded_at": note["recorded_at"]}]
            urgent.append(make_finding("urgent", message, evidence))
    return urgent


# ---------- step 4: group into one alert ----------

def group_findings(findings, urgent=()):
    all_findings = list(urgent) + findings
    if len(all_findings) == 0:
        return None

    if len(urgent) > 0:
        kind = "urgent"
        factors = ["urgent"]
    else:
        if len(findings) >= 2:
            kind = "combined"      # several areas changed together = a pattern
        else:
            kind = "single"
        factors = []
        for finding in findings:
            factors.append(finding["factor"])

    first_seen = all_findings[0]["first_seen"]
    last_seen = all_findings[0]["last_seen"]
    for finding in all_findings:
        if finding["first_seen"] < first_seen:
            first_seen = finding["first_seen"]
        if finding["last_seen"] > last_seen:
            last_seen = finding["last_seen"]

    return {
        "type": kind,
        "factors": factors,
        "findings": all_findings,
        "duration_days": (last_seen - first_seen).days + 1,   # used later for similar-case search
    }


# ---------- run everything ----------

def analyze(observations, notes, as_of):
    baseline = compute_baseline(observations, as_of)
    findings = detect_changes(observations, baseline, as_of)
    urgent = check_urgent(notes, as_of)
    return baseline, group_findings(findings, urgent)