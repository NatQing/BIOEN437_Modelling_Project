import json

from app import service
from app.examples import SPEC_EXAMPLE


def test_large_n_is_refused_gracefully():
    r = json.loads(service.run_ensemble_json(SPEC_EXAMPLE, 10, 1, 10_001, "", [], False))
    assert not r["ok"] and "limit" in r["error"]


def test_missing_values_reported_not_raised():
    r = json.loads(service.run_ensemble_json("A -> B; k\nA = 1", 10, 1, 10, "", [], False))
    assert not r["ok"] and r["error"].startswith("Line 1: no value given")


def test_bad_options():
    assert not json.loads(service.run_once(SPEC_EXAMPLE, 0, "", []))["ok"]
    assert not json.loads(service.run_ensemble_json(SPEC_EXAMPLE, 10, 0, 10, "", [], False))["ok"]
    assert not json.loads(service.run_ensemble_json(SPEC_EXAMPLE, 10, 1, 2.5, "", [], False))["ok"]


def test_run_once_and_seed_reported():
    r = json.loads(service.run_once(SPEC_EXAMPLE, 5, "42", ["A"]))
    assert r["ok"] and r["seed"] == 42 and r["csv"].startswith("time,A,B")
