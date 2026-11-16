import numpy as np
import pytest

from app.grid import make_grid, mean_sd, run_ensemble, sample_on_grid
from app.parser import parse_model


def test_make_grid():
    assert np.allclose(make_grid(10, 2.5), [0, 2.5, 5, 7.5, 10])
    assert np.allclose(make_grid(10, 3), [0, 3, 6, 9])      # floor(T/spacing)
    assert len(make_grid(1.0, 0.1)) == 11                   # float round-off must not drop the last point


def test_sampling_hand_made_trajectory_including_firing_on_grid_point():
    times = np.array([0.0, 1.0, 2.5, 4.0])
    counts = np.array([[10], [11], [12], [13]])
    grid = np.array([0.0, 1.0, 2.0, 3.0, 4.0, 5.0])
    out = sample_on_grid(times, counts, grid)[:, 0]
    # at t=1 and t=4 a firing lands exactly on the grid point: its new value is used
    assert out.tolist() == [10, 11, 11, 12, 13, 13]


def test_mean_sd_uses_ddof_1():
    samples = np.array([[1, 2], [3, 6]])
    mean, sd = mean_sd(samples)
    assert mean.tolist() == [2.0, 4.0]
    assert sd == pytest.approx([np.sqrt(2), np.sqrt(8)])


def test_single_run_sd_is_zero():
    mean, sd = mean_sd(np.array([[1, 2, 3]]))
    assert sd.tolist() == [0, 0, 0]


def test_deterministic_model_has_zero_sd():
    m = parse_model("A -> B; k\nA = 10; B = 0; k = 0")   # nothing ever fires
    ens = run_ensemble(m, 5, 1, 20, seed=1)
    assert np.all(ens.sd["A"] == 0) and np.all(ens.sd["B"] == 0)
    assert np.all(ens.mean["A"] == 10)


def test_ensemble_shape():
    m = parse_model("-> A; k\nA=0;k=1")
    ens = run_ensemble(m, 10, 2, 7, seed=3)
    assert ens.runs["A"].shape == (7, 6)
    assert np.all(ens.sd["A"][0] == 0) and np.all(ens.mean["A"][0] == 0)
