from petravigil.fixtures.loader import load_canonical_scenario


def test_canonical_fixture_is_explicitly_simulated_and_complete() -> None:
    scenario = load_canonical_scenario()

    assert scenario.scenario_id == "SC-HORMUZ-PARTIAL-BLOCKADE"
    assert scenario.status == "Simulated"
    assert scenario.risk_score.score == 0.78
    assert scenario.recommendations[0].recommendation_id == "PA-HORMUZ-001"
    assert scenario.approval.execution_external is False


def test_recommendation_evidence_references_exist() -> None:
    scenario = load_canonical_scenario()
    evidence_ids = {evidence.source_id for evidence in scenario.evidence}

    assert set(scenario.risk_event.evidence_ids).issubset(evidence_ids)
    assert set(scenario.recommendations[0].evidence_ids).issubset(evidence_ids)

