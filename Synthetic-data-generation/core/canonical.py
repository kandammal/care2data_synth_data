"""
Canonical Truth Layer — §2.1

SDTM is a rendered view. All generation and imputation operates on this
canonical truth model; SDTM is materialized from truth.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from datetime import date, timedelta
from typing import Optional, List, Dict, Tuple, Any, Any
from enum import Enum


# ─── Latent Trait Transforms (Contract 5) ────────────────────────────────────

MAX_FRAILTY_MULTIPLIER = 2.0


def frailty_to_multiplier(frailty_score: float) -> float:
    """Map latent frailty [0,1] to AE rate multiplier [0.5, 2.0]."""
    return 0.5 + 1.5 * frailty_score


def dropout_multiplier(frailty_score: float) -> float:
    """Map latent frailty [0,1] to dropout rate multiplier [0.6, 1.4]."""
    return 0.6 + 0.8 * frailty_score


def lab_trend_multiplier(baseline_severity: float) -> float:
    """Map baseline severity [0,1] to lab trend multiplier [0.8, 1.2]."""
    return 0.8 + 0.4 * baseline_severity


def mild_threshold(frailty_score: float) -> float:
    """CDF threshold for MILD severity."""
    return 0.50 - 0.15 * frailty_score


def moderate_threshold(frailty_score: float) -> float:
    """CDF threshold for MODERATE severity."""
    return 0.85 - 0.10 * frailty_score


# ─── Data Classes ────────────────────────────────────────────────────────────

@dataclass
class LatentTraits:
    """Cross-domain correlation drivers."""
    frailty_score: float = 0.5        # [0,1]
    adherence_propensity: float = 0.8  # [0,1]
    ae_susceptibility: float = 0.5     # [0,1]
    baseline_severity: float = 0.5     # [0,1]


@dataclass
class SubjectIdentity:
    """Stable identity fields."""
    canonical_id: str       # stable, never changes
    subject_index: int      # position in generation order (drives RNG)
    subjid: str
    siteid: str
    country: str


@dataclass
class ArmAssignment:
    """Treatment assignment for a single period."""
    period: int              # 1 for parallel; 1, 2, ... for crossover
    armcd: str               # treatment for this period
    epoch_label: str         # "TREATMENT" or "PERIOD 1", "PERIOD 2"
    start_day: int           # 1-based absolute study day this period starts
    end_day: int             # 1-based absolute study day this period ends (inclusive)
    washout_days_before: int = 0


@dataclass
class CrossoverSequence:
    """Crossover sequence definition."""
    seqcd: str               # "AB", "BA", "ABC", etc.
    periods: List[ArmAssignment] = field(default_factory=list)


@dataclass
class ElementSpan:
    """A span of time under a single element/epoch."""
    element: str
    start_day: int
    end_day: int
    epoch: str


@dataclass
class SubjectTimeline:
    """Temporal layout for a subject."""
    consent_date: date = field(default_factory=lambda: date(2024, 1, 15))
    screening_outcome: str = "PASSED"   # "PASSED" | "FAILED"
    element_spans: List[ElementSpan] = field(default_factory=list)
    total_study_days: int = 200          # protocol-planned
    exposure_days: int = 0               # sum of active treatment days
    exposure_fraction: float = 0.0
    end_date: Optional[date] = None
    first_dose_date: Optional[date] = None  # v2: stable first_dose_date for materializer


@dataclass
class SubjectDisposition:
    """Disposition outcome for the subject."""
    outcome: str = "COMPLETED"
    date: Optional[date] = None
    reason: str = ""
    linked_ae_id: Optional[str] = None  # canonical AE ID if AE caused discontinuation


@dataclass
class SubjectDeath:
    """Death information for the subject."""
    date: date = field(default_factory=lambda: date(2024, 6, 1))
    linked_ae_id: str = ""  # canonical AE ID of fatal AE


@dataclass
class AECandidate:
    """Pre-drawn AE candidate with stable identity (§2.2.1)."""
    canonical_id: str       # "AE_CAND_{k}"
    k: int                  # candidate slot index
    u_time: float           # Uniform(0,1) — shaped via Beta-PPF
    u_accept: float         # Uniform(0,1) — acceptance decision
    u_term: float           # Uniform(0,1) — maps to MedDRA term
    u_severity: float       # Uniform(0,1) — maps to severity
    u_duration: float       # Uniform(0,1) — maps to duration
    u_outcome: float        # Uniform(0,1) — maps to outcome


@dataclass
class AEEvent:
    """Accepted AE event in canonical truth."""
    canonical_id: str
    period: int
    onset_date: date = field(default_factory=lambda: date(2024, 3, 1))
    term: str = ""
    decoded_term: str = ""
    body_system: str = ""
    severity: str = "MILD"
    duration_days: int = 7
    outcome: str = "RECOVERED/RESOLVED"
    is_serious: bool = False
    is_fatal: bool = False
    relationship: str = "NOT RELATED"
    action: str = "DOSE NOT CHANGED"
    treatment_medication: Optional[str] = None  # CM linked
    # MedDRA hierarchy (Phase 2)
    pt_code: int = 0
    hlt_name: str = ""
    hlt_code: int = 0
    hlgt_name: str = ""
    hlgt_code: int = 0
    soc_name: str = ""
    soc_code: int = 0


@dataclass
class MHEvent:
    """Medical history condition in canonical truth."""
    canonical_id: str       # "MH_{k}"
    term: str = ""
    category: str = "GENERAL"
    subcategory: str = ""
    body_system: str = ""
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    is_ongoing: bool = False
    start_date_partial: str = ""  # ISO 8601 partial date (e.g., "2023-05")


@dataclass
class CMEvent:
    """Concomitant medication in canonical truth."""
    canonical_id: str       # "CM_{linked_ae_canonical_id}_{ordinal}" or "CM_STANDALONE_{k}"
    treatment: str = ""
    decoded: str = ""
    category: str = ""
    dose: float = 0.0
    dose_unit: str = "mg"
    frequency: str = "PRN"
    route: str = "ORAL"
    indication: str = ""
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    linked_ae_id: Optional[str] = None  # canonical AE ID if treating an AE
    linked_mh_term: Optional[str] = None  # MH condition if background med


@dataclass
class EXEvent:
    """Exposure record in canonical truth."""
    canonical_id: str       # "EX_{period}_{visit_anchor}"
    period: int = 1
    treatment: str = ""
    dose: float = 0.0
    dose_unit: str = "mg"
    form: str = ""
    frequency: str = "QD"
    route: str = "ORAL"
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    visit_anchor: Optional[str] = None


@dataclass
class VSRecord:
    """Vital sign measurement in canonical truth (record-keyed)."""
    canonical_id: str       # "VS_{period}_{visitnum}_{testcd}"
    period: int = 1
    visitnum: float = 1.0
    visit_label: str = ""
    testcd: str = ""
    test: str = ""
    value: float = 0.0
    unit: str = ""
    visit_date: Optional[date] = None
    study_day: Optional[int] = None
    is_missing: bool = False  # assessment-level missingness


@dataclass
class LBRecord:
    """Lab measurement in canonical truth (record-keyed)."""
    canonical_id: str       # "LB_{period}_{visitnum}_{testcd}"
    period: int = 1
    visitnum: float = 1.0
    visit_label: str = ""
    testcd: str = ""
    test: str = ""
    value: float = 0.0
    unit: str = ""
    visit_date: Optional[date] = None
    study_day: Optional[int] = None
    is_missing: bool = False  # assessment-level missingness
    nrind: str = ""           # NORMAL / HIGH / LOW
    lbornrlo: Optional[float] = None  # reference range low
    lbornrhi: Optional[float] = None  # reference range high


@dataclass
class Demographics:
    """Demographic fields."""
    age: int = 45
    sex: str = "M"
    race: str = "WHITE"
    ethnic: str = "NOT HISPANIC OR LATINO"


@dataclass
class CanonicalSubject:
    """
    Complete canonical truth for a single subject.

    SDTM is a rendered view of this model. All generation, imputation,
    and cascade logic operates on truth; SDTM is materialized from truth.
    """
    identity: SubjectIdentity = field(default_factory=lambda: SubjectIdentity(
        canonical_id="SUBJ_0", subject_index=0, subjid="001", siteid="SITE001", country="USA"
    ))

    latent_traits: LatentTraits = field(default_factory=LatentTraits)
    demographics: Demographics = field(default_factory=Demographics)

    # Treatment assignment
    treatment_sequence: List[ArmAssignment] = field(default_factory=list)
    arm_code: str = ""   # ARMCD for parallel; sequence code for crossover ("AB")
    arm_label: str = ""  # Human-readable arm label

    # Timeline
    timeline: SubjectTimeline = field(default_factory=SubjectTimeline)

    # Events (each with stable canonical ID)
    medical_history: List[MHEvent] = field(default_factory=list)
    adverse_events: List[AEEvent] = field(default_factory=list)
    exposures: List[EXEvent] = field(default_factory=list)
    conmeds: List[CMEvent] = field(default_factory=list)
    vs_records: List[VSRecord] = field(default_factory=list)
    lb_records: List[LBRecord] = field(default_factory=list)
    measurements: Dict[tuple, float] = field(default_factory=dict)  # (period, visit, test) → value

    # Disposition
    disposition: SubjectDisposition = field(default_factory=SubjectDisposition)

    # Death (optional)
    death: Optional[SubjectDeath] = None

    # Realism: baseline adjustments from demographics + MH conditioning
    baseline_adjustments: Optional[Any] = None  # realism.BaselineAdjustments

    @property
    def is_screen_failure(self) -> bool:
        return self.timeline.screening_outcome == "FAILED"

    @property
    def is_completed(self) -> bool:
        return self.disposition.outcome == "COMPLETED"

    @property
    def is_dead(self) -> bool:
        return self.death is not None

    @property
    def end_date(self) -> Optional[date]:
        if self.death:
            return self.death.date
        return self.timeline.end_date
