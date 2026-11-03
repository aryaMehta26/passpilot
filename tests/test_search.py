import math
import random

from passpilot.config import PASS_NAMES
from passpilot.evaluator import BudgetExhausted
from passpilot.search import crossover, genetic_search, mutate, random_pipeline, random_search


class FakeEvaluator:
    """Scores a pipeline without compiling anything: fewer 'dce' passes is faster."""

    def __init__(self, budget):
        self.budget, self.used, self.best, self.cache = budget, 0, (math.inf, None), {}

    @property
    def remaining(self):
        return self.budget - self.used

    def score(self, passes):
        key = tuple(passes)
        if key in self.cache:
            return self.cache[key]
        if self.remaining <= 0:
            raise BudgetExhausted
        self.used += 1
        s = 1.0 + passes.count("dce") + 0.01 * len(passes)
        self.cache[key] = s
        self.best = min(self.best, (s, list(passes)), key=lambda t: t[0])
        return s


def test_random_pipeline_length_and_names():
    rng = random.Random(1)
    for _ in range(50):
        p = random_pipeline(rng)
        assert 5 <= len(p) <= 30 and set(p) <= set(PASS_NAMES)


def test_mutate_and_crossover_stay_valid():
    rng = random.Random(2)
    a, b = random_pipeline(rng), random_pipeline(rng)
    for _ in range(200):
        a = mutate(a, rng)
        c = crossover(a, b, rng)
        assert 1 <= len(a) <= 40 and 1 <= len(c) <= 40
        assert set(a) <= set(PASS_NAMES) and set(c) <= set(PASS_NAMES)


def test_searches_respect_the_budget():
    for search in (random_search, genetic_search):
        ev = FakeEvaluator(budget=17)
        search(ev)
        assert ev.used == 17


def test_genetic_search_beats_its_first_generation():
    ev = FakeEvaluator(budget=200)
    genetic_search(ev, seed=3)
    first_gen_best = min(list(ev.cache.values())[:10])
    assert ev.best[0] < first_gen_best
