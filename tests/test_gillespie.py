import numpy as np

from app.examples import SPEC_EXAMPLE
from app.export import single_run_csv
from app.gillespie import gillespie, make_rng
from app.parser import parse_model
from app.plotting import plot_single


def test_trajectory_basics():
    m = parse_model(SPEC_EXAMPLE)
    t = gillespie(m, 10.0, make_rng(1))
    assert t.times[0] == 0.0
    assert np.all(np.diff(t.times) > 0)
    assert t.times[-1] <= 10.0
    assert np.all(t.counts >= 0)
    assert np.all(t.counts[:, m.species.index("X")] == 10)   # boundary never changes


def test_holds_state_when_nothing_can_happen():
    m = parse_model("A -> B; k\nA=0;B=3;k=1")
    t = gillespie(m, 5.0, make_rng(1))
    assert len(t.times) == 1


def test_csv_has_one_row_per_firing():
    m = parse_model(SPEC_EXAMPLE)
    t = gillespie(m, 10.0, make_rng(2))
    lines = single_run_csv(t).strip().split("\n")
    assert lines[0] == "time,A,B,C,D,X"
    assert len(lines) - 1 == len(t.times)   # t=0 row plus one row for each of the (len-1) firings


def test_plot_is_stepped():
    m = parse_model(SPEC_EXAMPLE)
    t = gillespie(m, 10.0, make_rng(2))
    fig = plot_single(t, ["A", "B"], 10.0)
    assert all(line.get_drawstyle() == "steps-post" for line in fig.axes[0].get_lines())
