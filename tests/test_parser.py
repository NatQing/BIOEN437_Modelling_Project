import pytest

from app.examples import SPEC_EXAMPLE
from app.parser import ParseError, parse_model


def test_spec_example_loads():
    m = parse_model(SPEC_EXAMPLE)
    assert m.species == ["A", "B", "C", "D", "X"]
    assert m.boundary == {"X"}
    assert [r.name for r in m.reactions] == ["J1", "J2", "J3", "J4", "J5", "J6"]
    assert m.initial == {"A": 100, "B": 50, "C": 0, "D": 0, "X": 10}
    assert m.constants["k3"] == 0.0005


def test_unnamed_reactions_numbered_in_order_and_alt_arrow():
    m = parse_model("A => B; k\nB -> A; k\nA = 1; B = 0; k = 1")
    assert [r.name for r in m.reactions] == ["J1", "J2"]


@pytest.mark.parametrize("text,line", [
    ("A = 1\nB = 0\nA + B ?? C; k\nk = 1", 3),                 # garbage line
    ("A = 1\nk = 1\n\nA -> ; ", 4),                           # reaction with an empty rate
    ("A = 1; k = 1\nA <-> B; k", 2),                          # reversible arrow
    ("A = 1; k = 1\n\n\nA -> 0.5 B; k", 4),                   # fractional stoichiometry
])
def test_broken_input_gives_correct_line(text, line):
    with pytest.raises(ParseError) as e:
        parse_model(text)
    assert e.value.line == line
    assert str(e.value).startswith(f"Line {line}: syntax error: ")


def test_missing_species_value():
    with pytest.raises(ParseError) as e:
        parse_model("A -> B; k\nA = 5\nk = 1")
    assert str(e.value) == "Line 1: no value given for 'B'"


def test_missing_rate_constant_value():
    with pytest.raises(ParseError) as e:
        parse_model("A = 1\nB = 0\n\nA -> B; k7")
    assert str(e.value) == "Line 4: no value given for 'k7'"


def test_bad_values():
    with pytest.raises(ParseError) as e:
        parse_model("A -> ; k\nA = 1.5\nk = 1")
    assert e.value.line == 2
    with pytest.raises(ParseError) as e:
        parse_model("A -> ; k\nA = 1\nk = -2")
    assert e.value.line == 3


def test_explicit_mass_action_accepted():
    m = parse_model("2 A -> D; k3*A*(A-1)/2\nA + B -> C; k1*A*B\nA=5;B=5;C=0;D=0;k3=1;k1=1")
    assert m.reactions[0].rate_name == "k3"


def test_non_mass_action_rejected():
    with pytest.raises(ParseError) as e:
        parse_model("A -> B; k*A*A\nA=1;B=0;k=1")
    assert e.value.line == 1
    with pytest.raises(ParseError):
        parse_model("A -> B; sin(k)*A\nA=1;B=0;k=1")


def test_empty_model():
    with pytest.raises(ParseError):
        parse_model("# nothing here")


def test_any_number_of_reactant_molecules():
    m = parse_model("3 A + B -> C; k\nA=5;B=2;C=0;k=1")
    assert m.reactions[0].reactants == {"A": 3, "B": 1}
