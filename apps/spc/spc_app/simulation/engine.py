"""Pure-Python simulation engine for the live SPC page."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TypedDict

import numpy as np


class ProcessConfig(TypedDict):
    label: str
    unit: str
    target_mu: float
    target_sigma: float


PROCESS_CONFIGS: dict[str, ProcessConfig] = {
    "Composites": {
        "label": "Ply Thickness",
        "unit": "mm",
        "target_mu": 0.250,
        "target_sigma": 0.001,
    },
    "Machining": {
        "label": "Hole Diameter",
        "unit": "mm",
        "target_mu": 10.000,
        "target_sigma": 0.005,
    },
}


@dataclass
class DisturbanceState:
    kind: str
    magnitude_sigma: float
    duration: int
    step_index: int = 0

    @property
    def steps_remaining(self) -> int:
        return max(0, self.duration - self.step_index)


class SimulationEngine:
    def __init__(self, process_stream: str = "Composites", subgroup_size: int = 5, rng_seed: int = 42) -> None:
        if process_stream not in PROCESS_CONFIGS:
            raise ValueError(f"Unknown process stream: {process_stream}")
        if subgroup_size < 1:
            raise ValueError("subgroup_size must be positive")

        self.process_stream = process_stream
        self.subgroup_size = subgroup_size
        self._rng_seed = rng_seed
        self._rng = np.random.default_rng(rng_seed)
        self.history: list[list[float]] = []
        self.active_disturbance: DisturbanceState | None = None
        self._load_process_defaults()

    def step(self) -> list[float]:
        mean_shift = self._mean_shift_for_step()
        subgroup = self._rng.normal(
            loc=self.target_mu + mean_shift,
            scale=self.target_sigma,
            size=self.subgroup_size,
        )
        subgroup_values = subgroup.tolist()
        self.history.append(subgroup_values)
        self._advance_disturbance()
        return subgroup_values

    def inject_mean_shift(self, magnitude_sigma: float = 1.5, duration: int = 10) -> None:
        self.active_disturbance = DisturbanceState(
            kind="mean_shift",
            magnitude_sigma=magnitude_sigma,
            duration=duration,
        )

    def inject_spike(self, magnitude_sigma: float = 4.0) -> None:
        self.active_disturbance = DisturbanceState(
            kind="spike",
            magnitude_sigma=magnitude_sigma,
            duration=1,
        )

    def inject_drift(self, max_sigma: float = 2.0, duration: int = 15) -> None:
        self.active_disturbance = DisturbanceState(
            kind="drift",
            magnitude_sigma=max_sigma,
            duration=duration,
        )

    def reset_disturbance(self) -> None:
        self.active_disturbance = None

    def reset(self) -> None:
        self.history = []
        self.active_disturbance = None
        self._rng = np.random.default_rng(self._rng_seed)
        self._load_process_defaults()

    @property
    def steps_generated(self) -> int:
        return len(self.history)

    def _load_process_defaults(self) -> None:
        config = PROCESS_CONFIGS[self.process_stream]
        self.target_mu = config["target_mu"]
        self.target_sigma = config["target_sigma"]

    def _mean_shift_for_step(self) -> float:
        if self.active_disturbance is None:
            return 0.0

        if self.active_disturbance.kind in {"mean_shift", "spike"}:
            return self.active_disturbance.magnitude_sigma * self.target_sigma

        if self.active_disturbance.kind == "drift":
            progress = (self.active_disturbance.step_index + 1) / self.active_disturbance.duration
            return progress * self.active_disturbance.magnitude_sigma * self.target_sigma

        return 0.0

    def _advance_disturbance(self) -> None:
        if self.active_disturbance is None:
            return

        self.active_disturbance.step_index += 1
        if self.active_disturbance.step_index >= self.active_disturbance.duration:
            self.active_disturbance = None
