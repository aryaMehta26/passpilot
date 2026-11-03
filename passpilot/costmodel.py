"""A learned cost model: predict a pipeline's speedup over -O3 before compiling it, then rank candidates.

Trained leave-one-benchmark-out: the model for benchmark X never sees X's measurements, so its ranking on X
is an honest test of whether it generalizes to an unseen program.
"""
import math
import random

import numpy as np
import pandas as pd
from scipy.stats import spearmanr
from xgboost import XGBRegressor

from .evaluator import BudgetExhausted
from .features import encode
from .search import mutate, random_pipeline


def _xy(rows):
    X = np.stack([encode(b, p.split()) for b, p in zip(rows.bench, rows.passes)])
    y = np.log(rows.speedup_vs_o3.to_numpy())
    return X, y


def usable(df):
    return df[df.correct.astype(bool) & df.speedup_vs_o3.notna()]


def train(df, exclude):
    rows = usable(df[df.bench != exclude])
    X, y = _xy(rows)
    model = XGBRegressor(n_estimators=300, max_depth=5, learning_rate=0.05, subsample=0.8,
                         colsample_bytree=0.8, random_state=0)
    model.fit(X, y)
    return model


def held_out_scores(df, bench, model):
    """Spearman rank correlation and whether the model's top pick is within 5% of the true best."""
    rows = usable(df[df.bench == bench])
    if len(rows) < 5:
        return {"bench": bench, "n": len(rows), "spearman": float("nan"), "top1_within_5pct": False}
    X, y = _xy(rows)
    pred = model.predict(X)
    rho = spearmanr(pred, y).statistic
    top1 = y[int(np.argmax(pred))] >= y.max() + math.log(0.95)
    return {"bench": bench, "n": len(rows), "spearman": float(rho), "top1_within_5pct": bool(top1)}


def model_guided_search(ev, model, train_df, n_candidates=3000, seed=0):
    """Score thousands of candidate pipelines with the model, then spend the real budget on the top ones.
    Candidates: random pipelines plus mutations of the best pipelines seen on *other* benchmarks."""
    rng = random.Random(seed)
    elite = usable(train_df[train_df.bench != ev.bench]).nlargest(50, "speedup_vs_o3").passes.str.split().tolist()
    cands = {tuple(random_pipeline(rng)) for _ in range(n_candidates // 2)}
    while len(cands) < n_candidates and elite:
        cands.add(tuple(mutate(rng.choice(elite), rng)))
    cands = list(cands)
    pred = model.predict(np.stack([encode(ev.bench, list(c)) for c in cands]))
    try:
        for i in np.argsort(-pred):
            if ev.remaining <= 0:
                break
            ev.score(list(cands[i]))
    except BudgetExhausted:
        pass
    return ev.best
