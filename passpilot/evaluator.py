"""One place every search method goes through: validates, measures, caches, and logs each candidate."""
import math
import time

from .config import SEARCH_RUNS
from .pipeline import InvalidPipeline, validate
from .toolchain import measure_passes


class Evaluator:
    def __init__(self, bench, method, budget, o3_runtime, log):
        self.bench, self.method, self.budget = bench, method, budget
        self.o3 = o3_runtime
        self.log = log          # shared list of row dicts, written to data/evaluations.csv
        self.cache = {}
        self.used = 0
        self.best = (math.inf, None)

    @property
    def remaining(self):
        return self.budget - self.used

    def score(self, passes):
        """Runtime in seconds; inf for anything that fails to build, crashes, or changes the output."""
        passes = tuple(validate(passes))
        if passes in self.cache:
            return self.cache[passes].runtime_s if self.cache[passes].correct else math.inf
        if self.remaining <= 0:
            raise BudgetExhausted
        self.used += 1
        t0 = time.perf_counter()
        m = measure_passes(self.bench, list(passes), SEARCH_RUNS, cutoff_s=1.5 * self.o3)
        self.cache[passes] = m
        s = m.runtime_s if (m.ok and m.correct) else math.inf
        if s < self.best[0]:
            self.best = (s, list(passes))
        self.log.append({"bench": self.bench, "method": self.method, "step": self.used,
                         "passes": " ".join(passes), "length": len(passes), "ok": m.ok, "correct": m.correct,
                         "runtime_s": m.runtime_s, "compile_s": m.compile_s, "text_bytes": m.text_bytes,
                         "speedup_vs_o3": self.o3 / m.runtime_s if s < math.inf else float("nan"),
                         "eval_s": time.perf_counter() - t0, "error": m.error})
        return s

    def result(self, passes):
        return self.cache[tuple(passes)]


class BudgetExhausted(Exception):
    pass


__all__ = ["Evaluator", "BudgetExhausted", "InvalidPipeline"]
