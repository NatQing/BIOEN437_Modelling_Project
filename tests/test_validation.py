import json
from pathlib import Path

import pytest

from app import validation

REF = Path(__file__).resolve().parent.parent / "reference" / "tellurium_reference.json"


def test_v1_steady_state_spread():
    r = validation.check_v1()
    assert r.passed, r.detail


def test_v2_against_tellurium_reference():
    if not REF.exists():
        pytest.skip("run reference/generate_reference.py first")
    r = validation.check_v2(json.loads(REF.read_text()))
    assert r.passed, r.detail


def test_v3_seed():
    r = validation.check_v3()
    assert r.passed, r.detail
