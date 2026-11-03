"""Baseline search strategies: random sampling and a genetic algorithm over pass sequences."""
import random

from .config import PASS_NAMES
from .evaluator import BudgetExhausted


def random_pipeline(rng, lo=5, hi=30):
    return [rng.choice(PASS_NAMES) for _ in range(rng.randint(lo, hi))]


def random_search(ev, seed=0):
    rng = random.Random(seed)
    try:
        while ev.remaining > 0:
            ev.score(random_pipeline(rng))
    except BudgetExhausted:
        pass
    return ev.best


def mutate(p, rng, max_len=40):
    p = list(p)
    op = rng.choice(["insert", "delete", "replace", "swap"])
    if op == "insert" and len(p) < max_len:
        p.insert(rng.randint(0, len(p)), rng.choice(PASS_NAMES))
    elif op == "delete" and len(p) > 1:
        del p[rng.randrange(len(p))]
    elif op == "replace":
        p[rng.randrange(len(p))] = rng.choice(PASS_NAMES)
    elif len(p) > 1:
        i, j = rng.sample(range(len(p)), 2)
        p[i], p[j] = p[j], p[i]
    return p


def crossover(a, b, rng, max_len=40):
    i, j = rng.randint(1, len(a)), rng.randint(0, len(b) - 1) if len(b) > 1 else 0
    return (a[:i] + b[j:])[:max_len]


def genetic_search(ev, seed=0, pop_size=10, elite=2, tournament=3, p_cross=0.7):
    """Steady generations: keep the elite, fill the rest by tournament selection, crossover and mutation."""
    rng = random.Random(seed)
    try:
        pop = [random_pipeline(rng) for _ in range(pop_size)]
        scored = [(ev.score(p), p) for p in pop]
        while ev.remaining > 0:
            scored.sort(key=lambda t: t[0])
            nxt = [p for _, p in scored[:elite]]

            def pick():
                return min(rng.sample(scored, tournament), key=lambda t: t[0])[1]

            while len(nxt) < pop_size:
                child = crossover(pick(), pick(), rng) if rng.random() < p_cross else list(pick())
                nxt.append(mutate(child, rng))
            scored = scored[:elite] + [(ev.score(p), p) for p in nxt[elite:]]
    except BudgetExhausted:
        pass
    return ev.best
