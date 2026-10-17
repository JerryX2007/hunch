import json
import time

from backend.app.models.parser import extract


note = """
October 17, 2026: Resident ate about half of breakfast.
They were much sleepier than usual during morning activities.
"""

start = time.perf_counter()
result = extract(note)
elapsed = time.perf_counter() - start

# Convert extracted observations to the format used by cases.json.
observations = []

for observation in result.observations:
    item = {
        "category": observation.category,
        "direction": observation.direction,
    }

    if observation.category == "toileting":
        item["subcategory"] = observation.subcategory
        item["change"] = observation.change

    observations.append(item)

print(json.dumps(observations, indent=2))
print(f"\nGemini took {elapsed:.2f} seconds")