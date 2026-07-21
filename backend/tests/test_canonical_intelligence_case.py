from fastapi.testclient import TestClient

from petravigil.main import app


client = TestClient(app)


def _propose(*, demand_bpd: int = 210_000, national_demand_lines: list[dict] | None = None) -> dict:
    payload: dict = {
        "text": "Shipping advisory reports tanker deviation and rising insurance premiums near Hormuz affecting India-bound crude cargoes.",
        "refinery": "Jamnagar",
        "required_volume_bpd": demand_bpd,
    }
    if national_demand_lines is not None:
        payload["national_demand_lines"] = national_demand_lines
    response = client.post("/api/v1/workflows/propose", json=payload)
    assert response.status_code == 201
    return response.json()


def _execute(proposal: dict) -> dict:
    response = client.post(
        f"/api/v1/workflows/{proposal['workflow_id']}/execute",
        json={
            "analyst_confirmed": True,
            "analyst_name": "Canonical Case Reviewer",
            "assumptions": proposal["proposed_assumptions"],
        },
    )
    assert response.status_code == 200
    return response.json()


def test_workflow_carries_one_source_labelled_case_through_to_national_impact(monkeypatch) -> None:
    """The judge flow is one case, not disconnected replay and allocator demos."""
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    proposal = _propose()

    case = proposal["case_context"]
    assert case["case_id"].startswith("CASE-")
    assert case["national_scope_status"] == "SIMULATED_NATIONAL_IMPACT_DRILL"
    assert case["replay_context"]["status"] == "LINKED"
    assert case["decision_clock_context"]["status"] == "LINKED"
    assert case["evidence_validation"]["requires_analyst_review"] is True
    assert case["evidence_validation"]["freshness_confidence"] == 0
    assert {entry["validation_status"] for entry in case["evidence_ledger"]} >= {
        "UNVERIFIED_USER_INPUT",
        "MODEL_PROPOSAL",
        "SEEDED_CONSTRAINT",
        "FIXTURE_CONTEXT",
    }

    workflow = _execute(proposal)
    assert workflow["status"] == "COMPLETED"
    assert workflow["case_context"]["case_id"] == case["case_id"]
    assert workflow["national_impact"]["status"] == "FEASIBLE"
    checks = {check["check_id"]: check for check in workflow["decision_safety_gate"]["checks"]}
    assert checks["EVIDENCE_VALIDATION"]["state"] == "WARNING"
    assert checks["NATIONAL_CAPACITY"]["state"] == "PASS"


def test_explicit_national_shortfall_blocks_the_same_workflow_case(monkeypatch) -> None:
    """A true national case cannot hide a shared-route shortfall behind a local portfolio."""
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    proposal = _propose(
        national_demand_lines=[
            {"refinery": "Jamnagar", "required_volume_bpd": 210_000},
            {"refinery": "Paradip", "required_volume_bpd": 240_000},
            {"refinery": "Kochi", "required_volume_bpd": 220_000},
        ]
    )
    assert proposal["case_context"]["national_scope_status"] == "EXPLICIT_NATIONAL_SCOPE"

    workflow = _execute(proposal)
    assert workflow["status"] == "BLOCKED"
    assert workflow["recommendation_id"] is None
    assert workflow["portfolios"] is None
    assert workflow["national_impact"]["status"] == "INFEASIBLE"
    national_check = next(
        check
        for check in workflow["decision_safety_gate"]["checks"]
        if check["check_id"] == "NATIONAL_CAPACITY"
    )
    assert national_check["state"] == "BLOCKER"
    assert national_check["summary"].startswith("No recommendation yet:")


def test_explicit_national_scope_must_reconcile_with_the_workflow_refinery() -> None:
    response = client.post(
        "/api/v1/workflows/propose",
        json={
            "text": "Shipping advisory reports tanker deviation and rising insurance premiums near Hormuz affecting India-bound crude cargoes.",
            "refinery": "Jamnagar",
            "required_volume_bpd": 210_000,
            "national_demand_lines": [
                {"refinery": "Paradip", "required_volume_bpd": 50_000},
                {"refinery": "Kochi", "required_volume_bpd": 80_000},
            ],
        },
    )

    assert response.status_code == 422
    assert "workflow refinery" in str(response.json()["detail"])
