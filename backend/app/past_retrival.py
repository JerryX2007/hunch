WEIGHT_OVERLAP = 0.7     # do the cases involve the same factors?
WEIGHT_DURATION = 0.3    # did the changes last a similar number of days?

TOP_N = 5                # how many cases to return


# ---------- small helpers ----------

def factor_of(obs):
    """Same naming as detection.py: toileting is split into urine / bowel."""
    if obs["category"] == "toileting":
        subcategory = obs.get("subcategory")
        if subcategory:
            return "toileting_" + subcategory
        return "toileting_other"
    return obs["category"]


def add_once(items, new_item):
    """Add to a list only if it isn't already there."""
    if new_item not in items:
        items.append(new_item)


def pairs_for_alert(alert):
    """
    The current alert as a list of (factor, direction) pairs.
    Everything detection flags is a worsening change, so direction is 'worsening'.
    """
    pairs = []
    for finding in alert["findings"]:
        if finding["factor"] == "urgent":
            continue
        add_once(pairs, (finding["factor"], "worsening"))
    return pairs


def pairs_for_case(case):
    """A historical case as a list of (factor, direction) pairs."""
    pairs = []
    for obs in case["observations"]:
        add_once(pairs, (factor_of(obs), obs["direction"]))
    return pairs


# ---------- the three small pieces of the search ----------

def split_pairs(alert_pairs, case_pairs):
    """Sort the pairs into: shared, only in the alert, only in the case."""
    shared = []
    only_alert = []
    only_case = []

    for pair in alert_pairs:
        if pair in case_pairs:
            shared.append(pair)
        else:
            only_alert.append(pair)

    for pair in case_pairs:
        if pair not in alert_pairs:
            only_case.append(pair)

    return shared, only_alert, only_case


def overlap_score(shared, only_alert, only_case):
    """0 to 1: shared pairs divided by all different pairs seen. (Jaccard score.)"""
    total = len(shared) + len(only_alert) + len(only_case)
    if total == 0:
        return 0.0
    return len(shared) / total


def duration_score(alert_days, case_days):
    """0 to 1: 1 means same length; falls to 0 when 7 or more days apart."""
    gap = abs(alert_days - case_days)
    if gap > 7:
        gap = 7
    return 1 - gap / 7


# ---------- the search ----------

def find_similar_cases(alert, cases, top_n=TOP_N):
    alert_pairs = pairs_for_alert(alert)

    results = []
    for case in cases:
        case_pairs = pairs_for_case(case)
        shared, only_alert, only_case = split_pairs(alert_pairs, case_pairs)

        # Skip cases that have nothing in common with the alert.
        if len(shared) == 0:
            continue

        overlap = overlap_score(shared, only_alert, only_case)
        duration = duration_score(alert["duration_days"], case["duration_days"])
        score = WEIGHT_OVERLAP * overlap + WEIGHT_DURATION * duration

        results.append({
            "case_id": case["id"],
            "score": round(score, 3),
            "matching": shared,
            "only_in_current_resident": only_alert,
            "only_in_this_case": only_case,
            "case_days": case["duration_days"],
            # Everything below is copied from the case library, never generated.
            "case_summary": case["case_summary"],
            "documented_outcome": case["documented_outcome"],
            "outcome_category": case.get("outcome_category"),
            "disposition": case.get("disposition"),
            "limitations": case["limitations"],
        })

    results.sort(key=get_score, reverse=True)
    return results[:top_n]


def get_score(result):
    return result["score"]