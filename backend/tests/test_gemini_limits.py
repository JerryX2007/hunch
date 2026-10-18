"""note_reader waits out Gemini's rate limits instead of failing every batch."""

import pytest

from app.models import note_reader as nr

RATE = ("429 RESOURCE_EXHAUSTED. {'error': {'code': 429, 'message': 'You exceeded your current quota... "
        "Please retry in 56.685845384s.'}}")


@pytest.fixture
def gemini(monkeypatch):
    slept, calls = [], []
    monkeypatch.setattr(nr.time, "sleep", lambda s: slept.append(s))
    monkeypatch.setenv("GEMINI_RPM", "6000")
    monkeypatch.setattr(nr, "_unusable", set())
    monkeypatch.setattr(nr, "_resting", {})
    monkeypatch.setattr(nr, "_pacer", nr._Pacer())
    monkeypatch.delenv("GEMINI_NOTE_MODEL", raising=False)
    monkeypatch.delenv("GEMINI_MODEL", raising=False)
    clock = [1000.0]
    monkeypatch.setattr(nr.time, "monotonic", lambda: clock[0])

    def sleep(s):
        slept.append(s)
        clock[0] += s
    monkeypatch.setattr(nr.time, "sleep", sleep)

    def use(answers):
        it = iter(answers)

        def call(model, notes):
            calls.append(model)
            a = next(it)
            if isinstance(a, Exception):
                raise a
            return [{"index": n["index"], "language": "en"} for n in notes]
        monkeypatch.setattr(nr, "_call", call)
    return use, slept, calls


def test_waits_for_the_rate_limit_then_reads(gemini):
    use, slept, calls = gemini
    use([RuntimeError(RATE), RuntimeError(RATE), "ok"])
    out = nr.read_notes(["Ate well.", "Drowsy."])
    assert out["model"] == nr.DEFAULT_MODEL and len(out["readings"]) == 2
    assert calls == [nr.DEFAULT_MODEL, nr.FALLBACK_MODEL, nr.DEFAULT_MODEL]  # tried the other model first
    assert any(s >= 56 for s in slept)  # waited as long as Gemini asked


def test_a_model_the_key_cannot_use_is_skipped_from_then_on(gemini):
    use, slept, calls = gemini
    use([RuntimeError("404 NOT_FOUND models/gemini-3.5-flash-lite"), "ok", "ok"])
    assert nr.read_notes(["a"])["model"] == nr.FALLBACK_MODEL
    assert nr.read_notes(["b"])["model"] == nr.FALLBACK_MODEL
    assert calls == [nr.DEFAULT_MODEL, nr.FALLBACK_MODEL, nr.FALLBACK_MODEL]


def test_a_daily_limit_gives_up_quickly(gemini):
    use, slept, calls = gemini
    daily = RuntimeError(RATE.replace("56.685845384s", "3600s"))
    use([daily, daily])
    with pytest.raises(nr.GeminiBusy):
        nr.read_notes(["a"])
    with pytest.raises(nr.GeminiBusy):  # the next batch doesn't even call: both models are resting
        nr.read_notes(["b"])
    assert len(calls) == 2 and not [s for s in slept if s > 1]


def test_saving_a_note_does_not_wait_long(gemini):
    use, slept, calls = gemini
    use([RuntimeError(RATE), RuntimeError(RATE)])
    with pytest.raises(nr.GeminiBusy):
        nr.read_notes(["a"], max_wait=20)
    assert not [s for s in slept if s > 1]


def test_other_errors_fail_the_batch_without_waiting(gemini):
    use, slept, calls = gemini
    use([RuntimeError("500 INTERNAL"), RuntimeError("500 INTERNAL")])
    with pytest.raises(RuntimeError):
        nr.read_notes(["a"])
    assert not [s for s in slept if s > 1] and len(calls) == 2
