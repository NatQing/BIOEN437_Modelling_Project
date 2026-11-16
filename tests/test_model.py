import numpy as np
import pytest

from app.examples import SPEC_EXAMPLE
from app.parser import parse_model


def prop(text, counts=None):
    m = parse_model(text)
    return m, m.propensities(counts or m.initial_counts())


def test_propensity_zero_order():
    assert prop("-> A; k\nA=3;k=2")[1] == [2.0]


def test_propensity_first_order():
    assert prop("A -> ; k\nA=7;k=0.5")[1] == [3.5]


def test_propensity_two_different_reactants():
    assert prop("A + B -> C; k\nA=4;B=5;C=0;k=0.1")[1] == [pytest.approx(2.0)]


def test_propensity_dimerisation():
    assert prop("2 A -> D; k\nA=10;D=0;k=0.2")[1] == [pytest.approx(0.2 * 10 * 9 / 2)]
    assert prop("2 A -> D; k\nA=1;D=0;k=0.2")[1] == [0.0]   # one molecule cannot dimerise


def test_propensity_three_molecules():
    assert prop("3 A -> ; k\nA=5;k=1")[1] == [pytest.approx(5 * 4 * 3 / 6)]


def test_boundary_species_used_in_propensity():
    m, a = prop("$X -> A; k\nA=0;X=10;k=0.2")
    assert a == [pytest.approx(2.0)]


def test_stoichiometry_matrix_and_boundary():
    m = parse_model(SPEC_EXAMPLE)
    N = m.stoichiometry_matrix()
    assert N.shape == (5, 6)
    # rows A,B,C,D,X ; columns J1..J6
    expected = np.array([
        [-1, 1, -2, 1, 0, 1],
        [-1, 1, 0, 0, 0, 0],
        [1, -1, 0, 0, 0, 0],
        [0, 0, 1, 0, -1, 0],
        [0, 0, 0, 0, 0, 0],   # boundary X never changes
    ])
    assert np.array_equal(N, expected)
