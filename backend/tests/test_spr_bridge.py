from fastapi.testclient import TestClient

from petravigil.main import app


client = TestClient(app)


def test_finite_spr_bridge_is_explicitly_authorized_and_covers_only_residual_capacity() -> None:
    """A high-demand case can use the finite bridge, never a fictitious reserve feed."""
    missing_authorization = client.post(
        "/api/v1/portfolios",
        json={
            "refinery": "Jamnagar",
            "required_volume_bpd": 300_000,
            "alternative_route_capacity_ratio": 0.72,
            "spr_bridge_opt_in": True,
        },
    )
    assert missing_authorization.status_code == 422
    assert "authorization" in str(missing_authorization.json()).lower()

    response = client.post(
        "/api/v1/portfolios",
        json={
            "refinery": "Jamnagar",
            "required_volume_bpd": 300_000,
            "alternative_route_capacity_ratio": 0.72,
            "spr_bridge_opt_in": True,
            "government_authorization_assumed_for_scenario": True,
            "spr_bridge_duration_days": 7,
        },
    )

    assert response.status_code == 201
    payload = response.json()
    assert payload["request"]["spr_bridge_opt_in"] is True
    assert payload["request"]["government_authorization_assumed_for_scenario"] is True

    supplied_portfolios = [item for item in payload["portfolios"] if item["label"] != "DO_NOTHING"]
    assert len(supplied_portfolios) == 3
    assert all(item["total_volume_bpd"] == 300_000 for item in supplied_portfolios)
    assert all(item["spr_bridge"]["status"] == "CONTINGENCY_ALLOCATED" for item in supplied_portfolios)

    for portfolio in supplied_portfolios:
        bridge = portfolio["spr_bridge"]
        external_total = sum(item["volume_bpd"] for item in portfolio["allocations"])
        assert external_total + bridge["bridge_volume_bpd"] == portfolio["total_volume_bpd"]
        assert 0 < bridge["bridge_volume_bpd"] <= bridge["seeded_capacity_bpd"] == 75_000
        assert 0 < bridge["bridge_duration_days"] <= bridge["seeded_max_bridge_days"] == 7
        assert bridge["bridge_volume_bbl"] == bridge["bridge_volume_bpd"] * bridge["bridge_duration_days"]
        assert bridge["data_status"] == "Simulated"
        assert bridge["capacity_source_status"] == "Simulated"
        assert bridge["authorization_source_status"] == "User-entered"
        assert bridge["requires_human_approval"] is True
        assert bridge["requires_government_authorization"] is True
        assert any("No live SPR inventory" in item for item in bridge["limitations"])


def test_workflow_carries_analyst_confirmed_spr_bridge_assumptions_into_selected_portfolio(monkeypatch) -> None:
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    proposed = client.post(
        "/api/v1/workflows/propose",
        json={
            "text": "Shipping advisory reports tanker deviation and rising insurance premiums near Hormuz affecting India-bound crude cargoes.",
            "refinery": "Jamnagar",
            "required_volume_bpd": 300_000,
        },
    )
    assert proposed.status_code == 201
    proposal = proposed.json()
    assumptions = proposal["proposed_assumptions"]
    assumptions.update(
        {
            "alternative_route_capacity_ratio": 0.72,
            "spr_bridge_opt_in": True,
            "government_authorization_assumed_for_scenario": True,
            "spr_bridge_duration_days": 7,
        }
    )

    executed = client.post(
        f"/api/v1/workflows/{proposal['workflow_id']}/execute",
        json={"analyst_confirmed": True, "analyst_name": "SPR contingency reviewer", "assumptions": assumptions},
    )

    assert executed.status_code == 200
    workflow = executed.json()
    assert workflow["status"] == "COMPLETED"
    assert workflow["portfolios"]["request"]["spr_bridge_opt_in"] is True
    selected_label = workflow["transparency"]["selected_portfolio"]
    selected = next(item for item in workflow["portfolios"]["portfolios"] if item["label"] == selected_label)
    assert selected["spr_bridge"]["status"] == "CONTINGENCY_ALLOCATED"
    assert selected["spr_bridge"]["analyst_opt_in"] is True
    assert "SPR bridge" in " ".join(workflow["transparency"]["assumptions"])

