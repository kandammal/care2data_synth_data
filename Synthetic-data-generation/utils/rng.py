"""
SDTM Synthetic Data Generator v2 — RNG Architecture

Hybrid per-subject + record-keyed + candidate pool RNG.
All derivations are pure functions with no mutable state or call-order dependence.

See architecture spec §2.2 for design rationale.
"""

import hashlib
import struct
import warnings
from enum import Enum
from typing import Optional, List

import numpy as np


# ─── Version Salt ────────────────────────────────────────────────────────────
GENERATOR_VERSION_SALT = "v2.0.0"


# ─── RNG Leaf Components ────────────────────────────────────────────────────
class RNGComponent(str, Enum):
    """All leaf components used as final key parts in draw() calls."""
    VALUE = "value"
    MISSING_FLAG = "missing_flag"
    NORMAL_RANGE_FLAG = "normal_range_flag"
    SEVERITY = "severity"
    DURATION = "duration"
    OUTCOME = "outcome"
    ACCEPT = "accept"
    TIME = "time"
    TERM = "term"
    DOSE = "dose"
    ROUTE = "route"
    FREQUENCY = "frequency"
    START_DATE = "start_date"
    END_DATE = "end_date"
    AGE = "age"
    SEX = "sex"
    RACE = "race"
    ETHNIC = "ethnic"
    SITE = "site"
    CONSENT_OFFSET = "consent_offset"
    SCREEN_FAIL = "screen_fail"
    DROPOUT = "dropout"
    DROPOUT_DAY = "dropout_day"
    DROPOUT_REASON = "dropout_reason"
    FRAILTY = "frailty"
    ADHERENCE = "adherence"
    AE_SUSCEPTIBILITY = "ae_susceptibility"
    BASELINE_SEVERITY = "baseline_severity"
    SERIOUS = "serious"
    RELATIONSHIP = "relationship"
    ACTION = "action"
    CONDITION = "condition"
    N_CONDITIONS = "n_conditions"
    ONGOING = "ongoing"
    MH_START = "mh_start"
    MH_END = "mh_end"
    BASELINE = "baseline"
    TREND = "trend"
    NOISE = "noise"
    VISIT_JITTER = "visit_jitter"
    CM_COUNT = "cm_count"
    CM_SELECTION = "cm_selection"
    CM_DOSE = "cm_dose"
    CM_DURATION = "cm_duration"
    SCREENING_DURATION = "screening_duration"
    DEATH_DELAY = "death_delay"
    # Realism layer components
    VISIT_ATTEND = "visit_attend"
    ASSESS_MISS_VS = "assess_miss_vs"
    ASSESS_MISS_LB = "assess_miss_lb"
    AR_STATE = "ar_state"
    MH_BG_CM_SELECT = "mh_bg_cm_select"
    AE_CM_SELECT = "ae_cm_select"
    PARTIAL_DATE = "partial_date"
    EX_DOSE_MOD = "ex_dose_mod"
    SCREEN_FAIL_DURATION = "screen_fail_duration"


class SubjectRNG:
    """
    Deterministic, order-independent RNG derivation for a single subject.
    
    Every method is a pure function: calling domain_rng("AE") before or after
    domain_rng("LB") produces identical results.
    """

    def __init__(self, study_seed: int, subject_index: int, protocol_id: str):
        self._base_entropy = (
            f"{study_seed}:{GENERATOR_VERSION_SALT}:{protocol_id}:{subject_index}"
        )
        self._seen_keys: set = set()

    def _derive(self, *components) -> np.random.Generator:
        """Pure derivation: hash(base_entropy + components) → deterministic RNG."""
        full_key = f"{self._base_entropy}:{'|'.join(str(c) for c in components)}"
        digest = hashlib.sha256(full_key.encode()).digest()
        entropy = list(struct.unpack('<8I', digest))
        return np.random.default_rng(np.random.SeedSequence(entropy))

    def domain_rng(self, domain: str) -> np.random.Generator:
        """Domain-level stream for demographics, timeline, disposition."""
        return self._derive(domain)

    def record_rng(self, domain: str, *key_parts) -> np.random.Generator:
        """Record-keyed stream for visit-anchored domains."""
        return self._derive(domain, *key_parts)

    def candidate_rng(self, domain: str, candidate_k: int) -> np.random.Generator:
        """Per-candidate stream for event domains using candidate pool."""
        return self._derive(domain, "candidate", candidate_k)

    def _check_key(self, key_components):
        """Unified key-reuse guard. Applies to all public draw methods."""
        if __debug__:
            key = key_components
            if key in self._seen_keys:
                warnings.warn(
                    f"Duplicate RNG key: {key}. This will produce "
                    f"identical draws — use a unique leaf component."
                )
            self._seen_keys.add(key)

    def draw(self, *key_components, n: int = 1) -> np.ndarray:
        """Draw n uniform(0,1) values for a fully-qualified key."""
        self._check_key(key_components)
        return self._derive(*key_components).random(n)

    def draw_normal(self, *key_components, mean: float = 0.0, std: float = 1.0) -> float:
        self._check_key(key_components)
        rng = self._derive(*key_components)
        return float(rng.normal(mean, std))

    def draw_int(self, *key_components, low: int = 0, high: int = 1) -> int:
        self._check_key(key_components)
        rng = self._derive(*key_components)
        return int(rng.integers(low, high + 1))

    def draw_choice(self, *key_components, items: list, weights: Optional[list] = None):
        self._check_key(key_components)
        rng = self._derive(*key_components)
        if weights is not None:
            w = np.array(weights, dtype=float)
            w = w / w.sum()
            return rng.choice(items, p=w)
        return rng.choice(items)

    def draw_from_dist(self, *key_components, distribution: dict) -> str:
        items = list(distribution.keys())
        weights = list(distribution.values())
        return self.draw_choice(*key_components, items=items, weights=weights)


def assign_arm(
    study_seed: int, protocol_id: str, subject_index: int,
    arm_order: list, subjects_per_arm: dict,
) -> str:
    """N-independent arm assignment via hashed uniform → cumulative ratio mapping."""
    rng = SubjectRNG(study_seed, subject_index, protocol_id)
    u = rng.draw("arm_assignment")[0]
    total_allocated = sum(subjects_per_arm[a] for a in arm_order)
    cumulative = 0.0
    for armcd in arm_order:
        cumulative += subjects_per_arm[armcd] / total_allocated
        if u < cumulative:
            return armcd
    return arm_order[-1]


# ─── Legacy Compatibility Layer ─────────────────────────────────────────────
_GLOBAL_SEED: Optional[int] = None
_GLOBAL_RNG = None


def set_seed(seed: int) -> None:
    global _GLOBAL_SEED, _GLOBAL_RNG
    _GLOBAL_SEED = seed
    _GLOBAL_RNG = SyntheticRNG(seed)


def set_global_seed(seed: int) -> None:
    set_seed(seed)


def get_rng(seed: Optional[int] = None):
    global _GLOBAL_RNG
    if seed is not None:
        return SyntheticRNG(seed)
    if _GLOBAL_RNG is None:
        _GLOBAL_RNG = SyntheticRNG(42)
    return _GLOBAL_RNG


class SyntheticRNG:
    """Legacy wrapper — used during migration only."""
    def __init__(self, seed: int = 42):
        self._rng = np.random.default_rng(seed)
        self._seed = seed

    def random(self): return float(self._rng.random())
    def randint(self, low, high): return int(self._rng.integers(low, high + 1))
    def choice(self, items, size=None, replace=True):
        if size is None: return self._rng.choice(items)
        return list(self._rng.choice(items, size=size, replace=replace))
    def weighted_choice(self, items, weights):
        w = np.array(weights); w = w / w.sum()
        return self._rng.choice(items, p=w)
    def normal(self, mean=0.0, std=1.0): return float(self._rng.normal(mean, std))
    def truncated_normal(self, mean, std, low, high):
        while True:
            v = self._rng.normal(mean, std)
            if low <= v <= high: return float(v)
    def uniform(self, low=0.0, high=1.0): return float(self._rng.uniform(low, high))
    def poisson(self, lam): return int(self._rng.poisson(lam))
    def binomial(self, n, p): return int(self._rng.binomial(n, p))
    def bernoulli(self, p): return self._rng.random() < p
    def shuffle(self, items):
        r = items.copy(); self._rng.shuffle(r); return r
    def sample_from_distribution(self, distribution, n=1):
        cats = list(distribution.keys())
        probs = np.array(list(distribution.values())); probs = probs / probs.sum()
        return list(self._rng.choice(cats, size=n, p=probs))


def random_choice(items, p=None, rng=None):
    if rng is None: rng = get_rng()
    return rng.weighted_choice(items, p) if p else rng.choice(items)

def random_int(low, high, rng=None):
    if rng is None: rng = get_rng()
    return rng.randint(low, high)

def random_normal(mean, sd, rng=None):
    if rng is None: rng = get_rng()
    return rng.normal(mean, sd)

def random_uniform(low, high, rng=None):
    if rng is None: rng = get_rng()
    return rng.uniform(low, high)

def random_poisson(lam, rng=None):
    if rng is None: rng = get_rng()
    return rng.poisson(lam)
