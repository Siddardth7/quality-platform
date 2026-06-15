"""Tests for the live-simulation engine (pure-Python logic)."""

import statistics

import pytest

from spc_app.simulation.engine import DisturbanceState, SimulationEngine


def test_init_rejects_unknown_process_stream():
    with pytest.raises(ValueError):
        SimulationEngine(process_stream="Nonexistent")


def test_init_rejects_nonpositive_subgroup_size():
    with pytest.raises(ValueError):
        SimulationEngine(subgroup_size=0)


def test_step_returns_subgroup_of_configured_size():
    engine = SimulationEngine(subgroup_size=5)
    subgroup = engine.step()
    assert isinstance(subgroup, list)
    assert len(subgroup) == 5


def test_step_accumulates_history_and_steps_generated():
    engine = SimulationEngine(subgroup_size=3)
    assert engine.steps_generated == 0
    engine.step()
    engine.step()
    assert engine.steps_generated == 2
    assert len(engine.history) == 2


def test_same_seed_produces_identical_first_step():
    a = SimulationEngine(rng_seed=123)
    b = SimulationEngine(rng_seed=123)
    assert a.step() == b.step()


def test_reset_clears_history_and_reseeds():
    engine = SimulationEngine(rng_seed=7)
    first = engine.step()
    engine.step()
    engine.reset()
    assert engine.steps_generated == 0
    assert engine.active_disturbance is None
    # Reseeded, so the next step reproduces the original first step.
    assert engine.step() == first


def test_machining_stream_loads_distinct_defaults():
    engine = SimulationEngine(process_stream="Machining")
    assert engine.target_mu == 10.000
    assert engine.target_sigma == 0.005


def test_inject_spike_lasts_one_step():
    engine = SimulationEngine()
    engine.inject_spike(magnitude_sigma=4.0)
    assert engine.active_disturbance is not None
    engine.step()
    assert engine.active_disturbance is None


def test_inject_mean_shift_lasts_its_duration():
    engine = SimulationEngine()
    engine.inject_mean_shift(magnitude_sigma=1.5, duration=3)
    engine.step()
    engine.step()
    assert engine.active_disturbance is not None  # 2 of 3 steps used
    engine.step()
    assert engine.active_disturbance is None  # 3rd step exhausts it


def test_mean_shift_raises_the_subgroup_mean():
    base = SimulationEngine(rng_seed=11)
    shifted = SimulationEngine(rng_seed=11)
    shifted.inject_mean_shift(magnitude_sigma=6.0, duration=5)
    # Same seed => same noise draw; the shifted engine adds +6 sigma to the mean.
    assert statistics.mean(shifted.step()) > statistics.mean(base.step())


def test_inject_drift_is_active_and_progresses():
    engine = SimulationEngine()
    engine.inject_drift(max_sigma=2.0, duration=4)
    assert engine.active_disturbance is not None
    assert engine.active_disturbance.kind == "drift"
    engine.step()  # exercises the drift branch of _mean_shift_for_step
    assert engine.active_disturbance.step_index == 1


def test_reset_disturbance_clears_active_disturbance():
    engine = SimulationEngine()
    engine.inject_drift()
    engine.reset_disturbance()
    assert engine.active_disturbance is None


def test_disturbance_state_steps_remaining():
    state = DisturbanceState(kind="mean_shift", magnitude_sigma=1.5, duration=10, step_index=3)
    assert state.steps_remaining == 7


def test_disturbance_state_steps_remaining_never_negative():
    state = DisturbanceState(kind="spike", magnitude_sigma=4.0, duration=1, step_index=5)
    assert state.steps_remaining == 0


def test_unknown_disturbance_kind_yields_no_mean_shift():
    # Defensive fall-through: an unrecognized kind contributes no shift.
    engine = SimulationEngine(rng_seed=11)
    baseline = SimulationEngine(rng_seed=11)
    engine.active_disturbance = DisturbanceState(
        kind="unrecognized", magnitude_sigma=5.0, duration=5
    )
    assert engine.step() == baseline.step()
