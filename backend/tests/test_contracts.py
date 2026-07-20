from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

from petravigil.models import (
    ApprovalDecision,
    ApprovalRecord,
    DataStatus,
    ProcurementRecommendation,
)


def test_approval_cannot_claim_external_execution() -> None:
    record = ApprovalRecord(
        approval_id="AP-TEST-001",
        recommendation_id="PA-TEST-001",
        decision=ApprovalDecision.DRAFT,
        decided_by="Test Analyst",
        decided_at=datetime.now(timezone.utc),
        justification="A local approval record is safe for the prototype.",
    )

    assert record.execution_external is False


def test_supply_recommendation_requires_concrete_details() -> None:
    with pytest.raises(ValidationError, match="supplier, grade, refinery, and route"):
        ProcurementRecommendation(
            recommendation_id="PA-TEST-002",
            status=DataStatus.SIMULATED,
            rank=1,
            action="INCREASE_VOLUME",
            volume_bpd=10_000,
            route_risk_score=0.2,
            confidence=0.8,
            rationale="This intentionally lacks required procurement details for validation.",
            feasibility_checks=[
                {"name": "GRADE", "passed": True, "rationale": "Prototype grade test passes with seeded data."}
            ],
            evidence_ids=["EV-TEST-001"],
        )

