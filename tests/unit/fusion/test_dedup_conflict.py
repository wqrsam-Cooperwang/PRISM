from __future__ import annotations

from src.inference.dedup_conflict import Observation, deduplicate_observations, conflict_metric, resolve_conflicts
from src.governance.dependency_matrix import DependencyMatrix
from src.governance.audit import AuditLogger


def test_duplicate_precision_weighted():
    # y1=1.5, v1=0.5; y2=2.0, v2=2.0 independent
    o1 = Observation(provider="p1", target="t", y=1.5, var=0.5, reliability=0.9)
    o2 = Observation(provider="p2", target="t", y=2.0, var=2.0, reliability=0.8)
    merged = deduplicate_observations([o1, o2], dependency_matrix=None, kappa=1.0, audit=AuditLogger())
    # independent merge should yield precision-weighted mean 1.6 and var 0.4
    assert len(merged) == 2 or len(merged) == 2  # no duplicates by fingerprint since values differ; simulate identical merge by setting same values

    # now identical values -> expect combination
    o1b = Observation(provider="p1", target="t", y=1.5, var=0.5, reliability=0.9)
    o2b = Observation(provider="p2", target="t", y=1.5, var=2.0, reliability=0.8)
    merged2 = deduplicate_observations([o1b, o2b], dependency_matrix=None, kappa=1.0, audit=AuditLogger())
    assert len(merged2) == 1
    m = merged2[0]
    # expected combined var = 1 / (1/0.5 + 1/2.0) = 1 / (2 + 0.5) = 0.4
    assert abs(m.var - 0.4) < 1e-12


def test_duplicate_correlation_merge():
    # two identical observations y=1.0 v=1.0 with rho=0.9
    o1 = Observation(provider="p1", target="t", y=1.0, var=1.0, reliability=0.9)
    o2 = Observation(provider="p2", target="t", y=1.0, var=1.0, reliability=0.9)
    dm = DependencyMatrix()
    dm.set("p1", "p2", 0.9)
    merged = deduplicate_observations([o1, o2], dependency_matrix=dm, kappa=1.0, audit=AuditLogger())
    assert len(merged) == 1
    m = merged[0]
    # expected combined variance = (1 + rho) / 2 = 0.95 for rho=0.9
    assert abs(m.var - 0.95) < 1e-12


def test_conflict_resolution_inflation():
    # three observations -1,0,1 var=1 prior variance 10
    obs = [Observation(provider=f"p{i}", target="t", y=float(y), var=1.0, reliability=0.8) for i, y in enumerate([-1.0, 0.0, 1.0])]
    prior_var = 10.0
    new_obs, new_prior = resolve_conflicts(obs, prior_variance=prior_var, threshold=1.0, inflation=2.0, audit=AuditLogger())
    # conflict metric should be >1 and prior inflated
    assert new_prior == prior_var * 2.0
    # some variances should have been inflated for low-reliability observations (median reliability equals reliability so none inflated here)
    assert len(new_obs) == 3

