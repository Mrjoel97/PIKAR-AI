import json
from pathlib import Path


DATASET_PATH = Path("tests/eval_datasets/persona_response_eval.json")
EXPECTED_PERSONAS = {"solopreneur", "startup", "sme", "enterprise"}



def test_persona_eval_dataset_has_full_persona_coverage_per_scenario() -> None:
    rows = json.loads(DATASET_PATH.read_text(encoding="utf-8"))

    scenarios: dict[str, set[str]] = {}
    for row in rows:
        scenarios.setdefault(row["scenario_id"], set()).add(row["persona"])
        assert row["expected_signals"]
        assert row["anti_signals"]
        assert row["agent_name"]
        assert row["prompt"]

    assert scenarios
    for personas in scenarios.values():
        assert personas == EXPECTED_PERSONAS