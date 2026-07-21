from fastapi.testclient import TestClient

from petravigil.fixtures.loader import load_hormuz_decision_clock
from petravigil.main import app


client = TestClient(app)


def test_hormuz_decision_clock_fixture_labels_every_quantitative_field() -> None:
    clock = load_hormuz_decision_clock()

    assert clock.clock_id == "CLK-HORMUZ-LOCAL-001"
    assert clock.replay_id == "RPL-HORMUZ-LOCAL-001"
    assert clock.base_decision_window_hours == 72
    assert clock.last_responsible_action_offset_hours == 72
    assert clock.usable_stock_cover_hours == 168
    assert {metric.key for metric in clock.metrics} == {
        "base_decision_window_hours",
        "stockout_threshold_hours",
        "baseline_approval_delay_hours",
        "laycan_cutoff_hours",
        "protected_inventory_buffer_hours",
        "usable_stock_cover_hours",
        "decision_lead_time_hours",
        "last_responsible_action_offset_hours",
        "effective_approval_delay_hours",
    }
    assert all(metric.source_status in {"Simulated", "Seeded", "User-entered"} for metric in clock.metrics)
    assert "does not use current inventory" in clock.disclaimer


def test_hormuz_decision_clock_endpoint_is_ordered_and_replay_linked() -> None:
    response = client.get("/api/v1/decision-clock/hormuz")

    assert response.status_code == 200
    payload = response.json()
    assert payload["replay_id"] == "RPL-HORMUZ-LOCAL-001"
    assert payload["effective_approval_delay_hours"] == 24
    assert payload["last_responsible_action_offset_hours"] == 72
    assert [stage["sequence"] for stage in payload["stages"]] == [1, 2, 3, 4, 5, 6]
    assert [stage["offset_hours"] for stage in payload["stages"]] == sorted(
        stage["offset_hours"] for stage in payload["stages"]
    )
    assert {stage["kind"] for stage in payload["stages"]} == {
        "SIGNAL",
        "ANALYST_REVIEW",
        "LAST_RESPONSIBLE_ACTION",
        "APPROVAL_COMPLETION",
        "LAYCAN_CUTOFF",
        "STOCKOUT_THRESHOLD",
    }


def test_decision_clock_recomputes_only_from_explicit_user_entered_approval_delay() -> None:
    response = client.get("/api/v1/decision-clock/hormuz?approval_delay_hours=48")

    assert response.status_code == 200
    payload = response.json()
    assert payload["effective_approval_delay_hours"] == 48
    assert payload["decision_lead_time_hours"] == 48
    assert payload["last_responsible_action_offset_hours"] == 48
    dynamic_metrics = {
        item["key"]: item for item in payload["metrics"] if item["key"] in {
            "effective_approval_delay_hours",
            "decision_lead_time_hours",
            "last_responsible_action_offset_hours",
        }
    }
    assert all(item["source_status"] == "User-entered" for item in dynamic_metrics.values())
    assert any(
        stage["kind"] == "LAST_RESPONSIBLE_ACTION"
        and stage["offset_hours"] == 48
        and stage["source_status"] == "User-entered"
        for stage in payload["stages"]
    )
