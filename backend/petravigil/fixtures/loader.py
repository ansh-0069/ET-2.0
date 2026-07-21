"""Fixture loading lives behind a small boundary so later phases can replace it."""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

from petravigil.models import CanonicalScenarioResponse, CrisisReplayResponse, DecisionClockResponse


FIXTURE_PATH = Path(__file__).with_name("hormuz_partial_blockade.json")
REPLAY_FIXTURE_PATH = Path(__file__).with_name("hormuz_crisis_replay.json")
DECISION_CLOCK_FIXTURE_PATH = Path(__file__).with_name("hormuz_decision_clock.json")


@lru_cache(maxsize=1)
def load_canonical_scenario() -> CanonicalScenarioResponse:
    with FIXTURE_PATH.open(encoding="utf-8") as fixture_file:
        return CanonicalScenarioResponse.model_validate(json.load(fixture_file))


@lru_cache(maxsize=1)
def load_hormuz_crisis_replay() -> CrisisReplayResponse:
    """Load the local, non-live Hormuz replay used by the map and demo flow."""
    with REPLAY_FIXTURE_PATH.open(encoding="utf-8") as fixture_file:
        return CrisisReplayResponse.model_validate(json.load(fixture_file))


@lru_cache(maxsize=1)
def load_hormuz_decision_clock() -> DecisionClockResponse:
    """Load the deterministic, non-live Hormuz Decision Clock fixture."""
    with DECISION_CLOCK_FIXTURE_PATH.open(encoding="utf-8") as fixture_file:
        return DecisionClockResponse.model_validate(json.load(fixture_file))


def load_hormuz_decision_clock_with_approval_delay(
    approval_delay_hours: int | None = None,
) -> DecisionClockResponse:
    """Return the static clock, optionally recomputed from a demo-only input.

    A supplied delay is intentionally labelled ``User-entered`` throughout the
    affected values; it is never mistaken for an observed approval duration.
    """
    clock = load_hormuz_decision_clock()
    if approval_delay_hours is None:
        return clock

    effective_delay = approval_delay_hours
    last_responsible_action = max(0, clock.laycan_cutoff_hours - effective_delay)
    source_status = "User-entered"
    replacement_values = {
        "effective_approval_delay_hours": effective_delay,
        "decision_lead_time_hours": last_responsible_action,
        "last_responsible_action_offset_hours": last_responsible_action,
    }
    metrics = []
    for metric in clock.metrics:
        if metric.key in replacement_values:
            updated_value = replacement_values[metric.key]
            if metric.key == "effective_approval_delay_hours":
                rationale = (
                    "This value was supplied by the local demo caller and is not an observed approval duration."
                )
            elif metric.key == "decision_lead_time_hours":
                rationale = (
                    "This local calculation uses the user-entered approval delay and seeded laycan cutoff; it is not live operational timing."
                )
            else:
                rationale = (
                    "This local deadline is derived from the user-entered approval delay and seeded laycan cutoff; it triggers no action."
                )
            metrics.append(metric.model_copy(update={"value": updated_value, "source_status": source_status, "rationale": rationale}))
        else:
            metrics.append(metric)

    stage_offsets = {
        "APPROVAL_COMPLETION": effective_delay,
        "LAST_RESPONSIBLE_ACTION": last_responsible_action,
    }
    stages = []
    for stage in clock.stages:
        if stage.kind in stage_offsets:
            offset = stage_offsets[stage.kind]
            if stage.kind == "APPROVAL_COMPLETION":
                detail = "This completion point uses a user-entered local demo value; it is not a measured approval duration."
            else:
                detail = (
                    "This local deadline is calculated from a user-entered approval delay and a seeded laycan cutoff; it creates no booking."
                )
            stages.append(stage.model_copy(update={"offset_hours": offset, "source_status": source_status, "detail": detail}))
        else:
            stages.append(stage)
    stage_priority = {"SIGNAL": 0, "LAST_RESPONSIBLE_ACTION": 1, "ANALYST_REVIEW": 2, "APPROVAL_COMPLETION": 3, "LAYCAN_CUTOFF": 4, "STOCKOUT_THRESHOLD": 5}
    stages = [
        stage.model_copy(update={"sequence": sequence})
        for sequence, stage in enumerate(
            sorted(stages, key=lambda stage: (stage.offset_hours, stage_priority[stage.kind])), start=1
        )
    ]

    assumptions = []
    for assumption in clock.assumptions:
        if assumption.assumption_id == "DCA-APPROVAL-001":
            assumptions.append(
                assumption.model_copy(
                    update={
                        "value": f"{effective_delay} hours",
                        "source_status": source_status,
                        "rationale": "This value was supplied through the local demo request and is not a real approval SLA or observation.",
                    }
                )
            )
        else:
            assumptions.append(assumption)

    payload = clock.model_dump(mode="python")
    payload.update(
        {
            "effective_approval_delay_hours": effective_delay,
            "decision_lead_time_hours": last_responsible_action,
            "last_responsible_action_offset_hours": last_responsible_action,
            "metrics": metrics,
            "stages": stages,
            "assumptions": assumptions,
        }
    )
    return DecisionClockResponse.model_validate(payload)
