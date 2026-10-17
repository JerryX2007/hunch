"""Print a ranked 2 West list from FICTIONAL data. Run:  python demo.py"""

from data.fake_unit import at, history, hunch, reading
from engine import Resident, Sign, score_unit

NOW = at(14, 20)

residents = [
    Resident("R01", "Harjit Kaur", "204", "B", flu_shot_this_season=False),
    Resident("R02", "Walter Lee", "206", "C", True, chronic_signs=frozenset({Sign.COUGHING})),
    Resident("R03", "Grace Okafor", "208", "A", True),
    Resident("R04", "Enzo Rossi", "210", "D", True),
    Resident("R05", "Mei Chen", "212", "B", True),
]

readings = []
for r, temp, fluids in [("R01", 36.2, 1280), ("R02", 36.7, 1100), ("R03", 36.5, 1300),
                        ("R04", 36.5, 1200), ("R05", 36.6, 1250)]:
    readings += history(r, "temp_c", temp, NOW, jitter=0.1)
    readings += history(r, "fluids_24h", fluids, NOW, jitter=60)

readings += [
    reading("R01", "temp_c", 37.5, at(14, 18)), reading("R01", "fluids_24h", 820, at(14, 19)),
    reading("R04", "temp_c", 36.6, at(14, 18)), reading("R04", "fluids_24h", 700, at(14, 19)),
]

hunches = [
    hunch("R01", "P1", Sign.SLEEPIER, at(14, 10)),
    hunch("R01", "P2", Sign.EATING_LESS, at(14, 13)),
    hunch("R01", "P3", Sign.SLEEPIER, at(14, 17)),
    hunch("R02", "P1", Sign.COUGHING, at(14, 11)),
    hunch("R03", "P2", Sign.WITHDRAWN, at(14, 12)),
    hunch("R04", "P1", Sign.CONFUSED, at(14, 10)),
    hunch("R04", "P4", Sign.NOT_DRINKING, at(14, 16)),
]

print("2 West - FICTIONAL DATA - scored at", NOW.strftime("%a %d %b %H:%M"), "\n")
for a in score_unit(residents, hunches, readings, NOW):
    print(f"[{a.tier:^8}] {a.resident.name:<13} score {a.score}")
    for line in a.reasons:
        print("     •", line)
    for note in a.notes:
        print("     ·", note)
    print()
