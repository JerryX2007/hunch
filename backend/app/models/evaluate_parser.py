
import time

from app.models.parser import extract


# Each test contains a care note and its expected observations.
# Each observation is:
# (category, direction, subcategory, change)

tests = [
    {
        "name": "Nutrition decline",
        "note": "The resident usually finishes breakfast but ate only a quarter today.",
        "expected": [
            ("nutrition", "worsening", None, None),
        ],
    },
    {
        "name": "Nutrition improvement",
        "note": "The resident's appetite has improved. They finished their entire lunch today after eating very little yesterday.",
        "expected": [
            ("nutrition", "improving", None, None),
        ],
    },
    {
        "name": "No clear change",
        "note": "The resident ate half of breakfast today. No usual intake or previous intake was documented.",
        "expected": [],
    },
    {
        "name": "Reduced fluid intake",
        "note": "The resident drank much less than usual today and needed repeated encouragement to drink.",
        "expected": [
            ("fluids", "worsening", None, None),
        ],
    },
    {
        "name": "Increased sleepiness",
        "note": "The resident was much sleepier than usual during morning activities.",
        "expected": [
            ("energy", "worsening", None, None),
        ],
    },
    {
        "name": "Mobility improvement",
        "note": "The resident now transfers with less assistance than yesterday and is walking more steadily.",
        "expected": [
            ("mobility", "improving", None, None),
        ],
    },
    {
        "name": "New confusion",
        "note": "The resident was oriented yesterday but repeatedly asked where they were today.",
        "expected": [
            ("confusion", "worsening", None, None),
        ],
    },
    {
        "name": "Pain improvement",
        "note": "The resident reported less knee pain today than yesterday.",
        "expected": [
            ("pain", "improving", None, None),
        ],
    },
    {
        "name": "Increased urination",
        "note": "The resident urinated more frequently than usual today.",
        "expected": [
            ("toileting", "worsening", "urine", "increased"),
        ],
    },
    {
        "name": "Multiple observations",
        "note": "Compared with usual, the resident ate less than half of their meals and slept through most afternoon activities.",
        "expected": [
            ("nutrition", "worsening", None, None),
            ("energy", "worsening", None, None),
        ],
    },
]


def observation_key(observation):
    return (
        observation.category,
        observation.direction,
        observation.subcategory,
        observation.change,
    )


passed = 0
failed = 0
errors = 0

for index, test in enumerate(tests):
    if index > 0:
        time.sleep(5)

    print(f"\nTest {index + 1}/{len(tests)}: {test['name']}")

    try:
        result = extract(test["note"])

        actual = sorted(
            observation_key(observation)
            for observation in result.observations
        )
        expected = sorted(test["expected"])

        if actual == expected:
            print("PASS")
            passed += 1
        else:
            print("FAIL")
            print("Expected:", expected)
            print("Actual:  ", actual)
            failed += 1

    except Exception as error:
        print("API / execution ERROR:", error)
        errors += 1

print("\n========== RESULTS ==========")
print(f"Passed: {passed}")
print(f"Failed: {failed}")
print(f"Errors: {errors}")
print(f"Completed: {passed + failed + errors}/{len(tests)}")

if passed + failed > 0:
    accuracy = passed / (passed + failed) * 100
    print(f"Accuracy on completed tests: {accuracy:.1f}%")
else:
    print("Accuracy unavailable: no tests completed successfully.")
