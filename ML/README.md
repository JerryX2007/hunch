# Hunch

PSW change-of-condition reports, scored against each resident's own baseline.
**All data in this repo is fictional.**

## Run it

```bash
pip install pyyaml pytest      # or: uv sync
pytest -v                      # 10 golden scenarios
python demo.py                 # ranked 2 West list with "why flagged" reasons
```

## Layout

| Path | What it is |
|---|---|
| `engine/models.py` | Data shapes: `Resident`, `Hunch`, `Reading`, the `Sign` vocabulary |
| `engine/shifts.py` | Which shift a timestamp belongs to (edit `SHIFT_STARTS`) |
| `engine/baseline.py` | Each resident's normal: median of 14 days ending 48 h ago |
| `engine/rules.py` | One small function per rule; each returns points + reason + evidence IDs |
| `engine/scoring.py` | Runs all rules, sums points, assigns Quiet / Watch / Assess / Call NP |
| `engine/weights.yaml` | Proposed points and thresholds - **not clinically validated** |
| `data/fake_unit.py` | Builders for fictional test data |
| `tests/test_scenarios.py` | Golden scenarios that must keep passing |
| `demo.py` | Prints the ranked unit list |
