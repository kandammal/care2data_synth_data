"""
Realism Layer — Cross-domain correlations, physiological conditioning,
pharmacological mappings, and temporal dynamics.

This module provides the intelligence that makes synthetic data behave
like real clinical trial data:
  - Demographics → baseline adjustments (age, sex, comorbidity effects)
  - MH → CM background medication mapping
  - AE → CM pharmacologically appropriate treatment mapping
  - AE → Lab/VS transient perturbations (feedback loops)
  - AR(1) state-space dynamics for within-subject autocorrelation
  - Weibull-distributed dropout timing (front-loaded)
  - Visit attendance and assessment-level missingness
  - Drug-class AE profiles for treatment-arm-specific rates
"""

from __future__ import annotations
import math
from dataclasses import dataclass, field
from datetime import date, timedelta
from typing import Dict, List, Optional, Tuple

# ─── Physiological Conditioning ──────────────────────────────────────────────

@dataclass
class BaselineAdjustments:
    """Per-subject baseline adjustments derived from demographics + MH."""
    vs_adjustments: Dict[str, float] = field(default_factory=dict)
    lb_adjustments: Dict[str, float] = field(default_factory=dict)
    ae_weight_modifiers: Dict[str, float] = field(default_factory=dict)
    extra_mh_prevalence_mult: float = 1.0


def compute_baseline_adjustments(
    age: int, sex: str, race: str,
    medical_history_terms: List[str],
) -> BaselineAdjustments:
    """
    Derive subject-specific baseline shifts from demographics and MH.

    Real lab/VS reference ranges vary by age, sex, and comorbidity burden.
    This function computes additive adjustments to the population means
    defined in the spec.
    """
    adj = BaselineAdjustments()
    mh_upper = {t.upper() for t in medical_history_terms}

    # ── Age effects ──
    age_offset = age - 50  # centered at 50
    adj.vs_adjustments['SYSBP'] = 0.4 * age_offset       # +0.4 mmHg per year over 50
    adj.vs_adjustments['DIABP'] = 0.15 * age_offset
    adj.vs_adjustments['PULSE'] = -0.05 * age_offset      # slight decrease with age
    adj.lb_adjustments['CREAT'] = 0.15 * max(age_offset, 0)  # renal decline after 50
    adj.lb_adjustments['GLUC'] = 0.02 * max(age_offset, 0)

    # ── Sex effects ──
    if sex == 'F':
        adj.lb_adjustments['HGB'] = -15.0        # female Hgb ~125 vs male ~140
        adj.lb_adjustments['CREAT'] = adj.lb_adjustments.get('CREAT', 0) - 15.0
        adj.vs_adjustments['SYSBP'] = adj.vs_adjustments.get('SYSBP', 0) - 5.0
        adj.vs_adjustments['WEIGHT'] = -10.0      # women ~60 vs men ~70 default
        adj.vs_adjustments['HEIGHT'] = -13.0      # women ~157 vs men ~170
    else:
        adj.vs_adjustments.setdefault('WEIGHT', 0.0)
        adj.vs_adjustments.setdefault('HEIGHT', 0.0)

    # ── Race effects (population-level means) ──
    if race == 'ASIAN':
        adj.vs_adjustments['WEIGHT'] = adj.vs_adjustments.get('WEIGHT', 0) - 8.0
        adj.vs_adjustments['HEIGHT'] = adj.vs_adjustments.get('HEIGHT', 0) - 5.0
    elif race == 'BLACK OR AFRICAN AMERICAN':
        adj.vs_adjustments['SYSBP'] = adj.vs_adjustments.get('SYSBP', 0) + 4.0
        adj.lb_adjustments['WBC'] = -0.8  # benign ethnic neutropenia

    # ── Medical history conditioning ──
    if 'HYPERTENSION' in mh_upper:
        adj.vs_adjustments['SYSBP'] = adj.vs_adjustments.get('SYSBP', 0) + 12.0
        adj.vs_adjustments['DIABP'] = adj.vs_adjustments.get('DIABP', 0) + 8.0
        adj.ae_weight_modifiers['Hypertension'] = 0.3  # reduce as AE (already has it)

    if 'DIABETES MELLITUS TYPE 2' in mh_upper or 'DIABETES MELLITUS' in mh_upper:
        adj.lb_adjustments['GLUC'] = adj.lb_adjustments.get('GLUC', 0) + 2.5
        adj.ae_weight_modifiers['Hyperglycaemia'] = 1.5

    if 'HYPERLIPIDEMIA' in mh_upper or 'HYPERLIPIDAEMIA' in mh_upper:
        # No dedicated lipid panel tests, but metabolic syndrome correlates:
        # elevated fasting glucose and slightly higher BMI/weight
        adj.lb_adjustments['GLUC'] = adj.lb_adjustments.get('GLUC', 0) + 0.8
        adj.vs_adjustments['WEIGHT'] = adj.vs_adjustments.get('WEIGHT', 0) + 3.0
        adj.ae_weight_modifiers['Myalgia'] = 1.3  # statin users have higher myalgia risk

    if 'ASTHMA' in mh_upper:
        adj.vs_adjustments['RESP'] = adj.vs_adjustments.get('RESP', 0) + 2.0
        adj.ae_weight_modifiers['Dyspnoea'] = 1.5

    if 'DEPRESSION' in mh_upper:
        adj.ae_weight_modifiers['Insomnia'] = 1.5
        adj.ae_weight_modifiers['Fatigue'] = 1.3

    # ── Comorbidity burden → more MH conditions for older subjects ──
    adj.extra_mh_prevalence_mult = 1.0 + 0.015 * max(age - 40, 0)

    return adj


# ─── AE → CM Pharmacological Mapping ────────────────────────────────────────

# Maps AE preferred terms (upper-cased) to clinically appropriate treatments
AE_TO_CM_MAP: Dict[str, List[Dict]] = {
    'HEADACHE': [
        {'cmtrt': 'PARACETAMOL', 'dose': 500, 'unit': 'mg', 'route': 'ORAL', 'freq': 'PRN'},
        {'cmtrt': 'IBUPROFEN', 'dose': 400, 'unit': 'mg', 'route': 'ORAL', 'freq': 'PRN'},
    ],
    'NAUSEA': [
        {'cmtrt': 'ONDANSETRON', 'dose': 4, 'unit': 'mg', 'route': 'ORAL', 'freq': 'PRN'},
        {'cmtrt': 'METOCLOPRAMIDE', 'dose': 10, 'unit': 'mg', 'route': 'ORAL', 'freq': 'TID'},
    ],
    'VOMITING': [
        {'cmtrt': 'ONDANSETRON', 'dose': 8, 'unit': 'mg', 'route': 'ORAL', 'freq': 'BID'},
    ],
    'DIARRHOEA': [
        {'cmtrt': 'LOPERAMIDE', 'dose': 2, 'unit': 'mg', 'route': 'ORAL', 'freq': 'PRN'},
    ],
    'DIARRHEA': [
        {'cmtrt': 'LOPERAMIDE', 'dose': 2, 'unit': 'mg', 'route': 'ORAL', 'freq': 'PRN'},
    ],
    'CONSTIPATION': [
        {'cmtrt': 'DOCUSATE SODIUM', 'dose': 100, 'unit': 'mg', 'route': 'ORAL', 'freq': 'BID'},
        {'cmtrt': 'POLYETHYLENE GLYCOL', 'dose': 17, 'unit': 'g', 'route': 'ORAL', 'freq': 'QD'},
    ],
    'RASH': [
        {'cmtrt': 'HYDROCORTISONE CREAM', 'dose': 1, 'unit': '%', 'route': 'TOPICAL', 'freq': 'BID'},
        {'cmtrt': 'CETIRIZINE', 'dose': 10, 'unit': 'mg', 'route': 'ORAL', 'freq': 'QD'},
    ],
    'PRURITUS': [
        {'cmtrt': 'CETIRIZINE', 'dose': 10, 'unit': 'mg', 'route': 'ORAL', 'freq': 'QD'},
        {'cmtrt': 'DIPHENHYDRAMINE', 'dose': 25, 'unit': 'mg', 'route': 'ORAL', 'freq': 'PRN'},
    ],
    'INSOMNIA': [
        {'cmtrt': 'MELATONIN', 'dose': 3, 'unit': 'mg', 'route': 'ORAL', 'freq': 'QD'},
        {'cmtrt': 'DIPHENHYDRAMINE', 'dose': 25, 'unit': 'mg', 'route': 'ORAL', 'freq': 'QD'},
    ],
    'BACK PAIN': [
        {'cmtrt': 'IBUPROFEN', 'dose': 400, 'unit': 'mg', 'route': 'ORAL', 'freq': 'TID'},
        {'cmtrt': 'PARACETAMOL', 'dose': 500, 'unit': 'mg', 'route': 'ORAL', 'freq': 'QID'},
    ],
    'ARTHRALGIA': [
        {'cmtrt': 'NAPROXEN', 'dose': 250, 'unit': 'mg', 'route': 'ORAL', 'freq': 'BID'},
        {'cmtrt': 'IBUPROFEN', 'dose': 400, 'unit': 'mg', 'route': 'ORAL', 'freq': 'TID'},
    ],
    'MYALGIA': [
        {'cmtrt': 'PARACETAMOL', 'dose': 500, 'unit': 'mg', 'route': 'ORAL', 'freq': 'PRN'},
    ],
    'PYREXIA': [
        {'cmtrt': 'PARACETAMOL', 'dose': 500, 'unit': 'mg', 'route': 'ORAL', 'freq': 'PRN'},
    ],
    'FATIGUE': [
        # Fatigue is usually managed supportively — no specific CM often
    ],
    'ABDOMINAL PAIN': [
        {'cmtrt': 'HYOSCINE BUTYLBROMIDE', 'dose': 10, 'unit': 'mg', 'route': 'ORAL', 'freq': 'TID'},
        {'cmtrt': 'PARACETAMOL', 'dose': 500, 'unit': 'mg', 'route': 'ORAL', 'freq': 'PRN'},
    ],
    'NASOPHARYNGITIS': [
        {'cmtrt': 'PARACETAMOL', 'dose': 500, 'unit': 'mg', 'route': 'ORAL', 'freq': 'PRN'},
    ],
    'UPPER RESPIRATORY TRACT INFECTION': [
        {'cmtrt': 'AMOXICILLIN', 'dose': 500, 'unit': 'mg', 'route': 'ORAL', 'freq': 'TID'},
        {'cmtrt': 'PARACETAMOL', 'dose': 500, 'unit': 'mg', 'route': 'ORAL', 'freq': 'PRN'},
    ],
    'HYPERTENSION': [
        {'cmtrt': 'AMLODIPINE', 'dose': 5, 'unit': 'mg', 'route': 'ORAL', 'freq': 'QD'},
    ],
    'DIZZINESS': [
        {'cmtrt': 'MECLIZINE', 'dose': 25, 'unit': 'mg', 'route': 'ORAL', 'freq': 'PRN'},
    ],
    'PNEUMONIA': [
        {'cmtrt': 'AMOXICILLIN/CLAVULANATE', 'dose': 875, 'unit': 'mg', 'route': 'ORAL', 'freq': 'BID'},
    ],
    'SOMNOLENCE': [],
    'INFECTION': [
        {'cmtrt': 'AMOXICILLIN', 'dose': 500, 'unit': 'mg', 'route': 'ORAL', 'freq': 'TID'},
    ],
    'INJECTION SITE REACTION': [
        {'cmtrt': 'HYDROCORTISONE CREAM', 'dose': 1, 'unit': '%', 'route': 'TOPICAL', 'freq': 'BID'},
    ],
}

# Fallback CM when AE term not in the mapping
DEFAULT_SYMPTOMATIC_CMS = [
    {'cmtrt': 'PARACETAMOL', 'dose': 500, 'unit': 'mg', 'route': 'ORAL', 'freq': 'PRN'},
    {'cmtrt': 'IBUPROFEN', 'dose': 400, 'unit': 'mg', 'route': 'ORAL', 'freq': 'PRN'},
]


def get_cm_for_ae(ae_term: str, u_select: float) -> Optional[Dict]:
    """
    Select a pharmacologically appropriate CM for an AE term.

    Returns None if no CM is indicated (e.g., Fatigue managed supportively).
    """
    term_upper = ae_term.strip().upper()
    candidates = AE_TO_CM_MAP.get(term_upper)

    if candidates is None:
        # Unknown term → use default symptomatic
        candidates = DEFAULT_SYMPTOMATIC_CMS

    if not candidates:
        return None

    idx = int(u_select * len(candidates))
    idx = min(idx, len(candidates) - 1)
    return candidates[idx]


# ─── MH → CM Background Medication Mapping ──────────────────────────────────

MH_TO_BACKGROUND_CM: Dict[str, List[Dict]] = {
    'HYPERTENSION': [
        {'cmtrt': 'LISINOPRIL', 'dose': 10, 'unit': 'mg', 'route': 'ORAL', 'freq': 'QD'},
        {'cmtrt': 'AMLODIPINE', 'dose': 5, 'unit': 'mg', 'route': 'ORAL', 'freq': 'QD'},
        {'cmtrt': 'HYDROCHLOROTHIAZIDE', 'dose': 25, 'unit': 'mg', 'route': 'ORAL', 'freq': 'QD'},
    ],
    'DIABETES MELLITUS TYPE 2': [
        {'cmtrt': 'METFORMIN', 'dose': 500, 'unit': 'mg', 'route': 'ORAL', 'freq': 'BID'},
        {'cmtrt': 'METFORMIN', 'dose': 1000, 'unit': 'mg', 'route': 'ORAL', 'freq': 'BID'},
    ],
    'DIABETES MELLITUS': [
        {'cmtrt': 'METFORMIN', 'dose': 500, 'unit': 'mg', 'route': 'ORAL', 'freq': 'BID'},
    ],
    'HYPERLIPIDEMIA': [
        {'cmtrt': 'ATORVASTATIN', 'dose': 20, 'unit': 'mg', 'route': 'ORAL', 'freq': 'QD'},
        {'cmtrt': 'ROSUVASTATIN', 'dose': 10, 'unit': 'mg', 'route': 'ORAL', 'freq': 'QD'},
    ],
    'HYPERLIPIDAEMIA': [
        {'cmtrt': 'ATORVASTATIN', 'dose': 20, 'unit': 'mg', 'route': 'ORAL', 'freq': 'QD'},
    ],
    'ASTHMA': [
        {'cmtrt': 'SALBUTAMOL', 'dose': 100, 'unit': 'mcg', 'route': 'INHALATION', 'freq': 'PRN'},
    ],
    'DEPRESSION': [
        {'cmtrt': 'SERTRALINE', 'dose': 50, 'unit': 'mg', 'route': 'ORAL', 'freq': 'QD'},
        {'cmtrt': 'ESCITALOPRAM', 'dose': 10, 'unit': 'mg', 'route': 'ORAL', 'freq': 'QD'},
    ],
    'GASTROESOPHAGEAL REFLUX DISEASE': [
        {'cmtrt': 'OMEPRAZOLE', 'dose': 20, 'unit': 'mg', 'route': 'ORAL', 'freq': 'QD'},
        {'cmtrt': 'ESOMEPRAZOLE', 'dose': 40, 'unit': 'mg', 'route': 'ORAL', 'freq': 'QD'},
    ],
    'HYPOTHYROIDISM': [
        {'cmtrt': 'LEVOTHYROXINE', 'dose': 50, 'unit': 'mcg', 'route': 'ORAL', 'freq': 'QD'},
    ],
}


def get_background_cm_for_mh(mh_term: str, u_select: float) -> Optional[Dict]:
    """Select a background medication appropriate for a medical history condition."""
    term_upper = mh_term.strip().upper()
    candidates = MH_TO_BACKGROUND_CM.get(term_upper)
    if not candidates:
        return None
    idx = int(u_select * len(candidates))
    idx = min(idx, len(candidates) - 1)
    return candidates[idx]


# ─── AE → Lab/VS Perturbation Mapping ───────────────────────────────────────

# Maps AE terms to transient lab/VS perturbations at nearby visits
# Each entry: {test_code: (additive_shift, proportional_to_severity)}
# Severity multipliers: MILD=0.5, MODERATE=1.0, SEVERE=1.5

AE_LAB_PERTURBATIONS: Dict[str, Dict[str, Tuple[float, bool]]] = {
    'ALANINE AMINOTRANSFERASE INCREASED': {
        'ALT': (80.0, True), 'AST': (40.0, True),
    },
    'HEPATOTOXICITY': {
        'ALT': (100.0, True), 'AST': (60.0, True),
    },
    'HYPERTENSION': {
        'SYSBP': (15.0, True), 'DIABP': (10.0, True),
    },
    'HYPOTENSION': {
        'SYSBP': (-20.0, True), 'DIABP': (-12.0, True),
    },
    'PYREXIA': {
        'TEMP': (1.5, True), 'PULSE': (10.0, True),
    },
    'TACHYCARDIA': {
        'PULSE': (20.0, True),
    },
    'ANAEMIA': {
        'HGB': (-20.0, True),
    },
    'ANEMIA': {
        'HGB': (-20.0, True),
    },
    'NEUTROPENIA': {
        'WBC': (-3.0, True),
    },
    'LYMPHOPENIA': {
        'WBC': (-2.0, True),
    },
    'THROMBOCYTOPENIA': {
        'PLAT': (-80.0, True),
    },
    'HYPERGLYCAEMIA': {
        'GLUC': (5.0, True),
    },
    'HYPERGLYCEMIA': {
        'GLUC': (5.0, True),
    },
    'DIARRHOEA': {
        'PULSE': (5.0, False),
    },
    'DIARRHEA': {
        'PULSE': (5.0, False),
    },
    'NAUSEA': {
        'WEIGHT': (-1.0, False),
    },
    'VOMITING': {
        'WEIGHT': (-1.5, False),
    },
}

SEVERITY_MULTIPLIERS = {'MILD': 0.5, 'MODERATE': 1.0, 'SEVERE': 1.5}


def compute_ae_perturbations(
    ae_events: list,
    visit_date: date,
    window_days: int = 14,
) -> Dict[str, float]:
    """
    Compute aggregate lab/VS perturbations from active AEs near a visit date.

    An AE contributes a perturbation if the visit falls within
    [ae_onset - 3 days, ae_onset + ae_duration + window_days].
    """
    perturbations: Dict[str, float] = {}

    for ae in ae_events:
        onset = ae.onset_date
        ae_end = onset + timedelta(days=ae.duration_days)
        # Window: AE is "active" from 3 days before onset to window_days after end
        if not (onset - timedelta(days=3) <= visit_date <= ae_end + timedelta(days=window_days)):
            continue

        term_upper = (ae.decoded_term or ae.term).strip().upper()
        ae_perturbs = AE_LAB_PERTURBATIONS.get(term_upper, {})
        sev_mult = SEVERITY_MULTIPLIERS.get(ae.severity, 1.0)

        for testcd, (shift, scales_with_severity) in ae_perturbs.items():
            effective = shift * sev_mult if scales_with_severity else shift
            # Decay: perturbation fades after AE resolution
            if visit_date > ae_end:
                days_past = (visit_date - ae_end).days
                decay = max(0.0, 1.0 - days_past / window_days)
                effective *= decay
            perturbations[testcd] = perturbations.get(testcd, 0.0) + effective

    return perturbations


# ─── AR(1) State-Space Dynamics ──────────────────────────────────────────────

# Per-test autocorrelation coefficients.
# BP/weight carry forward strongly; temperature and respiratory rate vary daily.
AR1_RHO_BY_TEST = {
    # VS tests
    'SYSBP': 0.85, 'DIABP': 0.85, 'PULSE': 0.70,
    'TEMP': 0.30, 'RESP': 0.40, 'WEIGHT': 0.95, 'HEIGHT': 0.99,
    # LB tests
    'ALT': 0.80, 'AST': 0.80, 'CREAT': 0.85,
    'GLUC': 0.60, 'HGB': 0.90, 'WBC': 0.50, 'PLAT': 0.75,
}


def get_ar1_rho(testcd: str, default_rho: float) -> float:
    """Get test-specific AR(1) rho, falling back to config default."""
    return AR1_RHO_BY_TEST.get(testcd, default_rho)


def ar1_next_state(
    prev_state: float,
    rho: float,
    innovation_sd: float,
    noise_draw: float,
) -> float:
    """
    Compute next AR(1) state.

    state[t] = rho * state[t-1] + sqrt(1 - rho^2) * sd * noise
    This ensures the marginal variance is sd^2.
    """
    innovation_scale = math.sqrt(max(1.0 - rho * rho, 0.01))
    return rho * prev_state + innovation_scale * innovation_sd * noise_draw


def treatment_effect_curve(
    days_on_treatment: int,
    e_max: float,
    tau_onset: float = 14.0,
    days_since_stop: int = 0,
    tau_washout: float = 7.0,
) -> float:
    """
    Pharmacokinetic-like treatment effect: onset → plateau → washout.

    Onset: E(t) = E_max * (1 - exp(-t / tau_onset))
    Washout: E(t) = E_plateau * exp(-t_off / tau_washout)
    """
    if days_on_treatment <= 0:
        return 0.0

    onset_effect = e_max * (1.0 - math.exp(-days_on_treatment / max(tau_onset, 1.0)))

    if days_since_stop > 0:
        return onset_effect * math.exp(-days_since_stop / max(tau_washout, 1.0))

    return onset_effect


# ─── Weibull Dropout Timing ──────────────────────────────────────────────────

def weibull_dropout_day(u: float, total_days: int, shape: float = 0.7) -> int:
    """
    Map a uniform draw to a Weibull-distributed dropout day.

    shape < 1 → decreasing hazard (front-loaded dropout — most realistic)
    shape = 1 → exponential (constant hazard)
    shape > 1 → increasing hazard

    Uses inverse CDF: F^{-1}(u) = total_days * (-ln(1-u))^{1/shape} / (-ln(epsilon))^{1/shape}
    Normalized so the support is [1, total_days].
    """
    if total_days <= 1:
        return 1
    u = max(1e-8, min(1.0 - 1e-8, u))
    # Inverse Weibull CDF, scaled to [0, 1]
    raw = (-math.log(1.0 - u)) ** (1.0 / shape)
    # Normalize: the 99.9th percentile maps to ~total_days
    scale = (-math.log(0.001)) ** (1.0 / shape)
    fraction = min(raw / scale, 1.0)
    day = max(1, int(fraction * total_days))
    return min(day, total_days)


# ─── Visit Missingness Model ────────────────────────────────────────────────

def should_miss_visit(
    u: float,
    base_rate: float = 0.07,
    visit_fraction: float = 0.5,
    adherence: float = 1.0,
) -> bool:
    """
    Determine if a scheduled visit is missed.

    Probability increases for:
    - Later visits (visit_fraction closer to 1.0)
    - Lower adherence subjects
    """
    # Increase miss rate for later visits and low-adherence subjects
    adherence_factor = 1.0 + 0.8 * (1.0 - adherence)
    time_factor = 1.0 + 0.5 * visit_fraction
    effective_rate = min(base_rate * adherence_factor * time_factor, 0.30)
    return u < effective_rate


def should_miss_assessment(u: float, domain_miss_rate: float = 0.03) -> bool:
    """
    Determine if a specific assessment is missing at an attended visit.

    Labs have slightly higher miss rate than vitals (blood draw refusal).
    """
    return u < domain_miss_rate


# ─── Lab Normal Range Flags ──────────────────────────────────────────────────

# Reference ranges: (low, high) by testcd
# Sex-stratified where clinically significant
LAB_REFERENCE_RANGES: Dict[str, Dict[str, Tuple[float, float]]] = {
    'ALT': {'default': (7, 56)},
    'AST': {'default': (10, 40)},
    'CREAT': {
        'M': (62, 106),  # umol/L
        'F': (44, 80),
        'default': (44, 106),
    },
    'GLUC': {'default': (3.9, 5.6)},  # fasting, mmol/L
    'HGB': {
        'M': (130, 175),  # g/L
        'F': (120, 155),
        'default': (120, 175),
    },
    'WBC': {'default': (4.0, 11.0)},  # 10^9/L
    'PLAT': {'default': (150, 400)},  # 10^9/L
}

VS_REFERENCE_RANGES: Dict[str, Tuple[float, float]] = {
    'SYSBP': (90, 140),
    'DIABP': (60, 90),
    'PULSE': (60, 100),
    'TEMP': (36.1, 37.2),
    'RESP': (12, 20),
}


def lab_normal_range_ind(testcd: str, value: float, sex: str = '') -> str:
    """Compute LBNRIND (normal range indicator): HIGH, LOW, or NORMAL."""
    ranges = LAB_REFERENCE_RANGES.get(testcd, {})
    if sex and sex in ranges:
        low, high = ranges[sex]
    elif 'default' in ranges:
        low, high = ranges['default']
    else:
        return ''

    if value < low:
        return 'LOW'
    elif value > high:
        return 'HIGH'
    else:
        return 'NORMAL'


def lab_reference_range(testcd: str, sex: str = '') -> Tuple[Optional[float], Optional[float]]:
    """Get (low, high) reference range for a lab test."""
    ranges = LAB_REFERENCE_RANGES.get(testcd, {})
    if sex and sex in ranges:
        return ranges[sex]
    return ranges.get('default', (None, None))


# ─── Partial Date Generation ────────────────────────────────────────────────

def maybe_partial_date(dt: date, u: float, partial_rate: float = 0.08) -> str:
    """
    Possibly return a partial ISO 8601 date (year-month only).

    Used for MH start dates and some AE end dates where exact day
    is often unknown in real data.
    """
    if u < partial_rate:
        return f"{dt.year:04d}-{dt.month:02d}"
    return dt.isoformat()


# ─── EX Dose Modification from AEs ──────────────────────────────────────────

@dataclass
class DoseModification:
    """Represents a dose change triggered by an AE."""
    ae_canonical_id: str
    modification_date: date
    action: str  # "INTERRUPTED", "REDUCED"
    interruption_days: int = 0
    dose_reduction_fraction: float = 1.0  # 0.5 = 50% of original


def derive_dose_modifications(
    ae_events: list,
    treatment_start: date,
    treatment_end: date,
) -> List[DoseModification]:
    """
    Derive EX dose modifications from AE actions.

    DRUG INTERRUPTED → gap in dosing for duration of AE
    DOSE REDUCED → remaining EX at reduced dose
    """
    mods = []
    for ae in ae_events:
        if ae.action == 'DRUG INTERRUPTED':
            if treatment_start <= ae.onset_date <= treatment_end:
                mods.append(DoseModification(
                    ae_canonical_id=ae.canonical_id,
                    modification_date=ae.onset_date,
                    action="INTERRUPTED",
                    interruption_days=min(ae.duration_days, (treatment_end - ae.onset_date).days),
                ))
        elif ae.action == 'DOSE REDUCED':
            if treatment_start <= ae.onset_date <= treatment_end:
                mods.append(DoseModification(
                    ae_canonical_id=ae.canonical_id,
                    modification_date=ae.onset_date,
                    action="REDUCED",
                    dose_reduction_fraction=0.5,
                ))
    # Sort by date
    mods.sort(key=lambda m: m.modification_date)
    return mods
