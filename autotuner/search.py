from __future__ import annotations

import math
import random
from typing import Any

from .core import Config, ConfigSpace


class SearchStrategy:
    """Strategies only receive the space and observations from their own evaluations."""

    def __init__(self, space: ConfigSpace, budget: int, seed: int = 0):
        if not 1 <= budget <= len(space.all()):
            raise ValueError("budget must be between one and the configuration-space size")
        self.configs, self.budget = space.all(), budget
        self.rng = random.Random(seed)
        self.observations: dict[Config, dict[str, Any]] = {}
        self.pending: Config | None = None

    def ask(self) -> Config | None:
        raise NotImplementedError

    def tell(self, config: Config, observation: dict[str, Any]) -> None:
        if config != self.pending or config in self.observations:
            raise ValueError("tell must correspond to one unobserved pending configuration")
        self.observations[config] = dict(observation)
        self.pending = None

    def score(self, config: Config) -> float:
        item = self.observations.get(config, {})
        value = item.get("score_seconds")
        if item.get("classification") == "success" and type(value) in (int, float) and math.isfinite(value) and value > 0:
            return value
        return math.inf

    def best(self) -> Config | None:
        valid = [config for config in self.observations if math.isfinite(self.score(config))]
        return min(valid, key=lambda config: (self.score(config), self.configs.index(config))) if valid else None

    def _ready(self) -> bool:
        if self.pending is not None:
            raise ValueError("pending configuration must be observed before next ask")
        return len(self.observations) < self.budget


class GridSearch(SearchStrategy):
    def __init__(self, space: ConfigSpace, budget: int | None = None, seed: int = 0):
        super().__init__(space, budget or len(space.all()), seed)

    def ask(self) -> Config | None:
        if not self._ready():
            return None
        self.pending = next(config for config in self.configs if config not in self.observations)
        return self.pending


class RandomSearch(SearchStrategy):
    def __init__(self, space: ConfigSpace, budget: int, seed: int = 0):
        super().__init__(space, budget, seed)
        self.order = list(self.configs)
        for index in range(len(self.order) - 1, 0, -1):
            other = self.rng.randrange(index + 1)
            self.order[index], self.order[other] = self.order[other], self.order[index]

    def ask(self) -> Config | None:
        if not self._ready():
            return None
        self.pending = next(config for config in self.order if config not in self.observations)
        return self.pending


class RestartGreedySearch(SearchStrategy):
    def __init__(self, space: ConfigSpace, budget: int, seed: int = 0):
        super().__init__(space, budget, seed)
        self.current: Config | None = None
        self.queue: list[Config] = []

    def neighbors(self, config: Config) -> tuple[Config, ...]:
        return tuple(candidate for candidate in self.configs
                     if (candidate.optimization != config.optimization)
                     + (candidate.block_size != config.block_size) == 1)

    def ask(self) -> Config | None:
        if not self._ready():
            return None
        while True:
            if self.current is None:
                self.current = self.rng.choice([config for config in self.configs if config not in self.observations])
                self.pending = self.current
                return self.pending
            if self.queue:
                self.pending = self.queue.pop(0)
                return self.pending
            unseen = [config for config in self.neighbors(self.current) if config not in self.observations]
            if unseen:
                self.rng.shuffle(unseen)
                self.queue = unseen
                continue
            best_neighbor = min(self.neighbors(self.current),
                                key=lambda config: (self.score(config), self.configs.index(config)))
            self.current = best_neighbor if self.score(best_neighbor) < self.score(self.current) else None
