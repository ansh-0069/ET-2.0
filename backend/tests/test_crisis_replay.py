from fastapi.testclient import TestClient

from petravigil.fixtures.loader import load_hormuz_crisis_replay
from petravigil.main import app


client = TestClient(app)


def test_hormuz_crisis_replay_fixture_is_ordered_and_explicitly_non_live() -> None:
    replay = load_hormuz_crisis_replay()
    payload = replay.model_dump(mode="json")

    assert replay.replay_id == "RPL-HORMUZ-LOCAL-001"
    assert [event.sequence for event in replay.evidence] == [1, 2, 3, 4]
    assert {route.status for route in replay.routes} == {"EXPOSED", "ALTERNATIVE"}
    assert all(len(route.coordinates) >= 2 for route in replay.routes)
    assert "Live API" not in str(payload)
    assert "not connected to live AIS" in replay.disclaimer


def test_hormuz_crisis_replay_endpoint_is_map_ready_and_source_labelled() -> None:
    response = client.get("/api/v1/replays/hormuz")

    assert response.status_code == 200
    payload = response.json()
    assert payload["chokepoint"] == "Strait of Hormuz"
    assert payload["evidence"][0]["source_status"] == "Simulated"
    assert payload["routes"][0]["status"] == "EXPOSED"
    assert payload["routes"][1]["status"] == "ALTERNATIVE"
    assert all(len(route["coordinates"]) >= 2 for route in payload["routes"])
    assert all(
        event["source_status"] in {"Simulated", "Historical", "User-entered"}
        for event in payload["evidence"]
    )
