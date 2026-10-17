import json
import re

# Words that sound like a diagnosis. The explanation must not use them.
BANNED_WORDS = [
    "infection", "infected", "dehydration", "dehydrated", "pneumonia", "uti",
    "sepsis", "delirium", "dementia", "depression", "diabetes", "stroke",
]

SYSTEM_PROMPT = """You write an evidence summary for a nurse in a long-term care home.

You are given a JSON object describing changes that were detected in one resident.
Use ONLY what is in that JSON.

Rules:
- Say what changed, when, and which observations support it.
- Every claim must list the evidence_ids it relies on. Use only IDs that appear in the JSON.
- Write at least one claim for every finding.
- Use only numbers and dates that appear in the JSON. Do not calculate new numbers.
- Do not name any medical condition or cause. Do not say what the changes mean medically.
- Do not suggest treatment or medication.
- In "uncertainties", say what the notes do not tell us. If a baseline is marked limited, say so.
- Keep each claim to one short sentence.

Return ONLY JSON in exactly this shape:
{
  "summary": "one or two sentences",
  "claims": [{"text": "one sentence", "evidence_ids": ["id1", "id2"]}],
  "uncertainties": ["one sentence"]
}"""


# ---------- step 1: build what we send to the LLM ----------

def describe_evidence(evidence_id, obs_by_id, notes_by_id):
    """Turn one evidence id into a small dictionary the LLM can read."""
    obs = obs_by_id.get(evidence_id)
    if obs is not None:
        excerpt = obs.get("evidence_span") or obs.get("observation_text") or ""
        return {
            "id": evidence_id,
            "date": str(obs["recorded_at"])[:10],
            "excerpt": excerpt,
            "value": obs.get("numeric_value"),
        }

    # Urgent findings point at a raw note instead of an observation.
    note = notes_by_id.get(evidence_id)
    if note is not None:
        return {
            "id": evidence_id,
            "date": str(note["recorded_at"])[:10],
            "excerpt": note["note_text"],
            "value": None,
        }
    return None


def build_llm_input(alert, baseline, observations, notes):
    """
    Returns (llm_input, allowed_ids).
    llm_input is everything the LLM is allowed to know.
    allowed_ids is the list of evidence ids it is allowed to cite.
    """
    obs_by_id = {}
    for obs in observations:
        obs_by_id[obs["id"]] = obs
    notes_by_id = {}
    for note in notes:
        notes_by_id[note["id"]] = note

    findings = []
    allowed_ids = []
    for finding in alert["findings"]:
        evidence = []
        for evidence_id in finding["evidence"]:
            item = describe_evidence(evidence_id, obs_by_id, notes_by_id)
            if item is not None:
                evidence.append(item)
                allowed_ids.append(evidence_id)

        entry = {
            "factor": finding["factor"],
            "summary": finding["message"],
            "evidence_count": len(evidence),
            "evidence": evidence,
        }
        if finding["factor"] in baseline:
            entry["baseline"] = baseline[finding["factor"]]
        findings.append(entry)

    first_seen = alert["findings"][0]["first_seen"]
    last_seen = alert["findings"][0]["last_seen"]
    for finding in alert["findings"]:
        if finding["first_seen"] < first_seen:
            first_seen = finding["first_seen"]
        if finding["last_seen"] > last_seen:
            last_seen = finding["last_seen"]

    llm_input = {
        "alert_type": alert["type"],
        "period": {
            "first_date": str(first_seen)[:10],
            "last_date": str(last_seen)[:10],
            "days": alert["duration_days"],
        },
        "number_of_areas_changed": len(findings),
        "findings": findings,
    }
    return llm_input, allowed_ids


def make_user_message(llm_input, previous_errors):
    message = json.dumps(llm_input, indent=2, default=str)
    if len(previous_errors) > 0:
        message += "\n\nYour previous answer was rejected for these reasons. Fix them:\n"
        for error in previous_errors:
            message += "- " + error + "\n"
    return message


# ---------- step 2: check the LLM's answer ----------

def numbers_in_text(text):
    return re.findall(r"\d+(?:\.\d+)?", text)


def allowed_numbers(llm_input):
    """Every number the LLM was given (dates, values, counts). Ids are left out on purpose."""
    pieces = [
        llm_input["period"]["first_date"],
        llm_input["period"]["last_date"],
        str(llm_input["period"]["days"]),
        str(llm_input["number_of_areas_changed"]),
    ]
    for finding in llm_input["findings"]:
        pieces.append(finding["summary"])
        pieces.append(str(finding["evidence_count"]))
        if "baseline" in finding:
            pieces.append(json.dumps(finding["baseline"], default=str))
        for item in finding["evidence"]:
            pieces.append(item["date"])
            pieces.append(item["excerpt"])
            pieces.append(str(item["value"]))

    allowed = set()
    for piece in pieces:
        for number in numbers_in_text(piece):
            allowed.add(number)
    return allowed


def all_text(answer):
    """Every sentence in the answer, so we can scan it."""
    texts = [answer["summary"]]
    for claim in answer["claims"]:
        texts.append(claim["text"])
    for line in answer["uncertainties"]:
        texts.append(line)
    return texts


def validate(answer, allowed_ids, llm_input):
    """Returns a list of problems. An empty list means the answer is OK."""
    errors = []

    # 1. Is it the right shape?
    if not isinstance(answer, dict):
        return ["the answer was not a JSON object"]
    if not isinstance(answer.get("summary"), str):
        errors.append("summary is missing")
    if not isinstance(answer.get("claims"), list) or len(answer.get("claims", [])) == 0:
        errors.append("claims are missing")
    if not isinstance(answer.get("uncertainties"), list) or len(answer.get("uncertainties", [])) == 0:
        errors.append("uncertainties are missing")
    if len(errors) > 0:
        return errors

    # 2. Does every claim cite real evidence?
    cited_ids = []
    for claim in answer["claims"]:
        ids = claim.get("evidence_ids")
        if not isinstance(claim.get("text"), str) or not isinstance(ids, list) or len(ids) == 0:
            errors.append("a claim has no text or no evidence_ids")
            continue
        for evidence_id in ids:
            if evidence_id not in allowed_ids:
                errors.append("unknown evidence id: " + str(evidence_id))
            else:
                cited_ids.append(evidence_id)

    # 3. Is every detected finding mentioned by at least one claim?
    for finding in llm_input["findings"]:
        covered = False
        for item in finding["evidence"]:
            if item["id"] in cited_ids:
                covered = True
        if not covered:
            errors.append("no claim covers the finding: " + finding["factor"])

    # 4. No invented numbers, no diagnosis words.
    allowed = allowed_numbers(llm_input)
    for text in all_text(answer):
        for number in numbers_in_text(text):
            if number not in allowed:
                errors.append("number not in the evidence: " + number)
        lowered = text.lower()
        for word in BANNED_WORDS:
            if re.search(r"\b" + word + r"\b", lowered):
                errors.append("diagnostic word used: " + word)

    return errors


# ---------- step 3: the fallback that needs no LLM ----------

def template_explanation(llm_input):
    """A plain, fully predictable explanation built straight from the findings."""
    names = []
    for finding in llm_input["findings"]:
        names.append(finding["factor"].replace("_", " "))

    period = llm_input["period"]
    summary = ("Changes were documented in " + ", ".join(names) + " between "
               + period["first_date"] + " and " + period["last_date"] + ".")

    claims = []
    limited = False
    for finding in llm_input["findings"]:
        ids = []
        for item in finding["evidence"]:
            ids.append(item["id"])
        claims.append({"text": finding["summary"] + ".", "evidence_ids": ids})
        if finding.get("baseline", {}).get("limited"):
            limited = True

    uncertainties = ["These observations do not establish a cause. "
                     "A qualified staff member should review the resident."]
    if limited:
        uncertainties.append("The baseline is based on limited history.")

    return {"summary": summary, "claims": claims, "uncertainties": uncertainties}


# ---------- run everything ----------

def explain(alert, baseline, observations, notes, llm=None):
    """
    llm is a function: llm(system_prompt, user_message) -> dict (already parsed JSON).
    Returns (explanation, source) where source is "llm" or "template".
    """
    llm_input, allowed_ids = build_llm_input(alert, baseline, observations, notes)

    if llm is None:
        return template_explanation(llm_input), "template"

    errors = []
    for attempt in range(2):
        try:
            answer = llm(SYSTEM_PROMPT, make_user_message(llm_input, errors))
        except Exception:
            errors = ["the call failed or did not return valid JSON"]
            continue

        errors = validate(answer, allowed_ids, llm_input)
        if len(errors) == 0:
            return answer, "llm"

    return template_explanation(llm_input), "template"