import pytest

from app.examples import SPEC_EXAMPLE
from app.export import ensemble_csv, to_antimony
from app.grid import run_ensemble
from app.parser import parse_model


def test_export_has_explicit_mass_action():
    text = to_antimony(parse_model(SPEC_EXAMPLE))
    assert "J1: A + B -> C; k1*A*B" in text
    assert "J3: 2 A -> D; k3*A*(A-1)/2" in text
    assert "J4: -> A; k4" in text
    assert "J6: X -> A; k6*X" in text
    assert "const species X" in text


def test_export_round_trip():
    m = parse_model(SPEC_EXAMPLE)
    m2 = parse_model(to_antimony(m))
    assert m2.species == m.species and m2.initial == m.initial and m2.boundary == m.boundary
    assert m2.constants == m.constants
    counts = [7, 4, 2, 3, 10]
    assert m2.propensities(counts) == m.propensities(counts)


def test_ensemble_csv_one_row_per_grid_point():
    m = parse_model("-> A; k\nA=0;k=1")
    ens = run_ensemble(m, 4, 1, 5, seed=1)
    lines = ensemble_csv(ens).strip().split("\n")
    assert lines[0] == "time,A_mean,A_sd"
    assert len(lines) == 1 + 5


def test_export_loads_in_tellurium_and_matches_propensities():
    te = pytest.importorskip("tellurium")
    m = parse_model(SPEC_EXAMPLE)
    r = te.loada(to_antimony(m))
    counts = dict(zip(m.species, m.initial_counts()))
    ours = dict(zip([x.name for x in m.reactions], m.propensities(m.initial_counts())))
    theirs = dict(zip(r.getReactionIds(), r.getReactionRates()))
    for name, a in ours.items():
        assert theirs[name] == pytest.approx(a), counts
