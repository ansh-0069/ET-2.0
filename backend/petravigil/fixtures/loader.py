"""Fixture loading lives behind a small boundary so later phases can replace it."""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

from petravigil.models import CanonicalScenarioResponse


FIXTURE_PATH = Path(__file__).with_name("hormuz_partial_blockade.json")


@lru_cache(maxsize=1)
def load_canonical_scenario() -> CanonicalScenarioResponse:
    with FIXTURE_PATH.open(encoding="utf-8") as fixture_file:
        return CanonicalScenarioResponse.model_validate(json.load(fixture_file))

