"""
Subject-Level Generation Pipeline — §2.4

When any truth value changes for a subject, regenerate all SDTM records.
No incremental/partial updates.

Seven-stage pipeline:
  Stage 1: Build PLANNED timeline from protocol spec
  Stage 2: Generate candidate AEs against PLANNED timeline
  Stage 3: Derive disposition from accepted AEs
  Stage 4: Apply censoring — set actual end_date from disposition
  Stage 5: Derive remaining events (CM, EX, VS, LB)
  Stage 6: Materialize SDTM and compute all derived fields
  Stage 7: Constraint validation
"""

from __future__ import annotations
import math
import warnings
from datetime import date, timedelta
from typing import Optional, List, Dict, Tuple, Any

import numpy as np

from .canonical import (
    CanonicalSubject, LatentTraits, SubjectIdentity, Demographics,
    SubjectTimeline, SubjectDisposition, SubjectDeath, ElementSpan,
    ArmAssignment, CrossoverSequence, AECandidate, AEEvent,
    MHEvent, CMEvent, EXEvent, VSRecord, LBRecord,
    frailty_to_multiplier, dropout_multiplier, MAX_FRAILTY_MULTIPLIER,
    mild_threshold, moderate_threshold, lab_trend_multiplier,
)
from .provenance import ProvenanceMap, CanonicalRelationship
from .realism import (
    compute_baseline_adjustments, BaselineAdjustments,
    get_cm_for_ae, get_background_cm_for_mh,
    compute_ae_perturbations, AE_LAB_PERTURBATIONS,
    ar1_next_state, treatment_effect_curve,
    weibull_dropout_day,
    should_miss_visit, should_miss_assessment,
    lab_normal_range_ind, lab_reference_range,
    maybe_partial_date,
    derive_dose_modifications, DoseModification,
    get_ar1_rho,
)
from ..utils.rng import SubjectRNG, RNGComponent, assign_arm
from ..spec.models import TrialDesignSpec
from ..terminology.meddra_terms import (
    MedDRATerm, CORE_MEDDRA_TERMS, get_term_library, meddra_term_to_dict,
    PROTOCOL_TERM_LIBRARIES, get_all_meddra_terms,
)

# Try importing scipy for Beta-PPF (optional, falls back to uniform)
try:
    from scipy.stats import beta as beta_dist
    HAS_SCIPY = True
except ImportError:
    HAS_SCIPY = False


# ─── Default AE Term Library ────────────────────────────────────────────────
# Now uses MedDRA terms as primary source; legacy dicts as fallback
DEFAULT_AE_TERMS = [meddra_term_to_dict(t) for t in CORE_MEDDRA_TERMS]

# ─── Default MH Conditions ──────────────────────────────────────────────────
DEFAULT_MH_CONDITIONS = [
    {'term': 'HYPERTENSION', 'cat': 'CARDIOVASCULAR', 'prev': 0.3},
    {'term': 'DIABETES MELLITUS TYPE 2', 'cat': 'ENDOCRINE', 'prev': 0.15},
    {'term': 'HYPERLIPIDEMIA', 'cat': 'METABOLIC', 'prev': 0.25},
    {'term': 'ASTHMA', 'cat': 'RESPIRATORY', 'prev': 0.08},
    {'term': 'DEPRESSION', 'cat': 'PSYCHIATRIC', 'prev': 0.1},
    {'term': 'GASTROESOPHAGEAL REFLUX DISEASE', 'cat': 'GASTROINTESTINAL', 'prev': 0.15},
]

# ─── Default CM Library ─────────────────────────────────────────────────────
DEFAULT_CM_LIBRARY = [
    {'cmtrt': 'PARACETAMOL', 'cmroute': 'ORAL', 'cmdosfrq': 'PRN'},
    {'cmtrt': 'IBUPROFEN', 'cmroute': 'ORAL', 'cmdosfrq': 'PRN'},
    {'cmtrt': 'OMEPRAZOLE', 'cmroute': 'ORAL', 'cmdosfrq': 'QD'},
    {'cmtrt': 'METFORMIN', 'cmroute': 'ORAL', 'cmdosfrq': 'BID'},
    {'cmtrt': 'ASPIRIN', 'cmroute': 'ORAL', 'cmdosfrq': 'QD'},
]


def compute_pool_size(spec: TrialDesignSpec) -> int:
    """Conservative pool size per Contract 4 (v12).
    
    Uses spec.ae_model.computed_pool_size if cached at spec-resolution time.
    Falls back to runtime computation only for specs not resolved through
    the standard TrialDesignSpecResolver path (e.g., test fixtures).
    """
    if spec.ae_model.pool_size > 0:
        return spec.ae_model.pool_size
    
    # Use cached value from _finalize_spec (Contract 4 compliance)
    if spec.ae_model.computed_pool_size is not None:
        return spec.ae_model.computed_pool_size
    
    # Fallback for test specs not resolved through the standard path
    total_study_days = spec.compute_total_study_days()
    max_exposure_months = total_study_days / 30.0
    min_P_exp = min_shaped_exposure_probability(spec)
    
    lambda_eff_max = (
        spec.ae_model.ae_rate_multiplier
        * max_exposure_months
        * MAX_FRAILTY_MULTIPLIER
    ) / min_P_exp
    
    M = math.ceil(lambda_eff_max + 6 * math.sqrt(max(lambda_eff_max, 1)))
    return max(M, 30)


def min_shaped_exposure_probability(spec: TrialDesignSpec) -> float:
    """Worst-case shaped exposure probability across all sequences (Contract 4).
    
    Uses cached min_p_exp from spec.ae_model when available (set at resolution time).
    Falls back to runtime computation for test specs.
    """
    # Use cached value if available (Contract 4)
    if spec.ae_model.min_p_exp is not None:
        return spec.ae_model.min_p_exp
    
    # Fallback for test specs
    a, b = spec.ae_model.time_shape_params
    total = spec.compute_total_study_days()
    
    if total <= 0:
        return 1e-6
    
    def _compute_p_exp(treatment_sequence: List[ArmAssignment]) -> float:
        if a == 1.0 and b == 1.0:
            exposure_days = sum(p.end_day - p.start_day + 1 for p in treatment_sequence)
            return max(exposure_days / total, 1e-6)
        if not HAS_SCIPY:
            exposure_days = sum(p.end_day - p.start_day + 1 for p in treatment_sequence)
            return max(exposure_days / total, 1e-6)
        p = 0.0
        for period in treatment_sequence:
            lo = (period.start_day - 1) / total
            hi = period.end_day / total
            p += beta_dist.cdf(hi, a, b) - beta_dist.cdf(lo, a, b)
        return max(p, 1e-6)
    
    probs = []
    if spec.is_crossover and spec.crossover_sequences:
        for seq_def in spec.crossover_sequences:
            periods_data = seq_def['periods'] if isinstance(seq_def, dict) else seq_def.periods
            ts = [
                ArmAssignment(
                    period=p['period'] if isinstance(p, dict) else p.period,
                    armcd=p['armcd'] if isinstance(p, dict) else p.armcd,
                    epoch_label=p.get('epoch', '') if isinstance(p, dict) else getattr(p, 'epoch', ''),
                    start_day=p['start_day'] if isinstance(p, dict) else p.start_day,
                    end_day=p['end_day'] if isinstance(p, dict) else p.end_day,
                )
                for p in periods_data
            ]
            probs.append(_compute_p_exp(ts))
    else:
        for arm in spec.arms:
            ts = _build_treatment_sequence(spec, arm.armcd)
            probs.append(_compute_p_exp(ts))
    
    return min(probs) if probs else 1.0


def generate_canonical_subject(
    spec: TrialDesignSpec,
    subject_index: int,
    study_seed: int,
) -> CanonicalSubject:
    """
    Generate a complete CanonicalSubject through the 7-stage pipeline.
    
    This is the primary entry point for subject generation.
    """
    protocol_id = spec.study_id
    rng = SubjectRNG(study_seed, subject_index, protocol_id)
    
    # ── Identity ──
    n_sites = spec.demographics.n_sites
    site_idx = subject_index % n_sites
    siteid = spec.demographics.sites[site_idx] if site_idx < len(spec.demographics.sites) else f"SITE{site_idx+1:03d}"
    subjid = f"{subject_index + 1:04d}"
    usubjid = f"{spec.study_id}-{siteid}-{subjid}"
    
    identity = SubjectIdentity(
        canonical_id=f"SUBJ_{subject_index}",
        subject_index=subject_index,
        subjid=subjid,
        siteid=siteid,
        country=spec.demographics.country,
    )
    
    # ── Latent Traits ──
    latent_traits = LatentTraits(
        frailty_score=float(rng.draw("DM", RNGComponent.FRAILTY)[0]),
        adherence_propensity=float(rng.draw("DM", RNGComponent.ADHERENCE)[0]),
        ae_susceptibility=float(rng.draw("DM", RNGComponent.AE_SUSCEPTIBILITY)[0]),
        baseline_severity=float(rng.draw("DM", RNGComponent.BASELINE_SEVERITY)[0]),
    )
    
    # ── Demographics ──
    demos = spec.demographics
    age_u = rng.draw("DM", RNGComponent.AGE)[0]
    # Map uniform to truncated normal via inverse CDF approximation
    age_raw = demos.age_mean + demos.age_sd * _inv_normal_approx(age_u)
    age = int(max(demos.age_min, min(demos.age_max, age_raw)))
    
    sex = rng.draw_from_dist("DM", RNGComponent.SEX, distribution=demos.sex_distribution)
    race = rng.draw_from_dist("DM", RNGComponent.RACE, distribution=demos.race_distribution)
    ethnic = rng.draw_from_dist("DM", RNGComponent.ETHNIC, distribution=demos.ethnic_distribution)
    
    demographics = Demographics(age=age, sex=sex, race=race, ethnic=ethnic)
    
    # ── Arm Assignment (N-independent) ──
    if spec.is_crossover and spec.crossover_sequences:
        # For crossover: assign a sequence code (e.g., "AB", "BA")
        seq_codes = [s['seqcd'] if isinstance(s, dict) else s.seqcd for s in spec.crossover_sequences]
        subjects_per_arm = spec.demographics.subjects_per_arm
        if not subjects_per_arm:
            subjects_per_arm = {s: 1 for s in seq_codes}
        armcd = assign_arm(study_seed, protocol_id, subject_index, seq_codes, subjects_per_arm)
        arm_label = _get_crossover_label(spec, armcd)
    else:
        arm_order = spec.get_arm_order_list()
        subjects_per_arm = spec.demographics.subjects_per_arm
        if not subjects_per_arm:
            subjects_per_arm = {a: 1 for a in arm_order}
        armcd = assign_arm(study_seed, protocol_id, subject_index, arm_order, subjects_per_arm)
    
    arm_spec = spec.get_arm_by_armcd(armcd)
    if arm_spec:
        arm_label = arm_spec.arm if arm_spec else armcd
    elif not spec.is_crossover:
        arm_label = armcd
    
    # ── Stage 1: Build PLANNED timeline ──
    disp = spec.disposition_model
    total_study_days = spec.compute_total_study_days()
    
    # Consent date
    study_start = spec.time_conventions.study_start_date_default
    jitter = spec.time_conventions.study_start_date_jitter_days
    consent_offset = rng.draw_int("timeline", RNGComponent.CONSENT_OFFSET, low=0, high=jitter)
    consent_date = study_start + timedelta(days=consent_offset)
    
    # Screen failure check
    screen_fail_u = rng.draw("timeline", RNGComponent.SCREEN_FAIL)[0]
    is_screen_failure = screen_fail_u < disp.screen_fail_rate
    
    if is_screen_failure:
        # Screen failures: minimal timeline, no treatment
        screen_fail_days = rng.draw_int("timeline", RNGComponent.SCREEN_FAIL_DURATION, low=1, high=28)
        end_date = consent_date + timedelta(days=screen_fail_days)
        
        subject = CanonicalSubject(
            identity=identity,
            latent_traits=latent_traits,
            demographics=demographics,
            arm_code=armcd,
            arm_label=arm_label,
            treatment_sequence=[],
            timeline=SubjectTimeline(
                consent_date=consent_date,
                screening_outcome="FAILED",
                total_study_days=total_study_days,
                end_date=end_date,
            ),
            disposition=SubjectDisposition(
                outcome="SCREEN FAILURE",
                date=end_date,
                reason="SCREEN FAILURE",
            ),
        )
        return subject
    
    # Build treatment sequence (parallel = single period)
    treatment_sequence = _build_treatment_sequence(spec, armcd)
    
    # Compute exposure fields
    exposure_days = sum(p.end_day - p.start_day + 1 for p in treatment_sequence)
    exposure_fraction = exposure_days / total_study_days if total_study_days > 0 else 0.0
    
    # Screening duration → first dose date
    screening_duration = rng.draw_int("timeline", RNGComponent.SCREENING_DURATION, low=7, high=35)
    first_dose_date = consent_date + timedelta(days=screening_duration)
    
    # Build element spans
    element_spans = _build_element_spans(spec, armcd)
    
    # Planned end date
    planned_end = first_dose_date + timedelta(days=total_study_days - 1)
    
    timeline = SubjectTimeline(
        consent_date=consent_date,
        screening_outcome="PASSED",
        element_spans=element_spans,
        total_study_days=total_study_days,
        exposure_days=exposure_days,
        exposure_fraction=exposure_fraction,
        end_date=planned_end,
        first_dose_date=first_dose_date,
    )
    
    # ── Stage 2: Generate candidate AEs ──
    M = compute_pool_size(spec)
    subj_canonical_id = identity.canonical_id  # P0: subject-scope all canonical IDs
    candidates = _generate_ae_candidates(rng, M, subj_canonical_id)
    
    # Build temporary subject for acceptance
    subject = CanonicalSubject(
        identity=identity,
        latent_traits=latent_traits,
        demographics=demographics,
        arm_code=armcd,
        arm_label=arm_label,
        treatment_sequence=treatment_sequence,
        timeline=timeline,
    )
    
    accepted_aes = _accept_ae_candidates(candidates, subject, spec, rng, first_dose_date)
    
    # ── Stage 3: Derive disposition from accepted AEs ──
    # Use Weibull-distributed dropout timing if enabled
    disposition, death = _derive_disposition(
        accepted_aes, subject, spec, rng, first_dose_date, planned_end
    )
    subject.disposition = disposition
    subject.death = death
    
    # ── Stage 4: Apply censoring ──
    actual_end = disposition.date or planned_end
    if death:
        actual_end = death.date
    
    timeline.end_date = actual_end
    
    # Drop AEs after actual end
    accepted_aes = [ae for ae in accepted_aes if ae.onset_date <= actual_end]
    
    # Truncate ongoing AEs at end date
    for ae in accepted_aes:
        ae_end = ae.onset_date + timedelta(days=ae.duration_days)
        if ae_end > actual_end:
            ae.duration_days = (actual_end - ae.onset_date).days
    
    subject.adverse_events = accepted_aes
    
    # ── Stage 5: Derive remaining events ──
    # Medical History
    subject.medical_history = _generate_medical_history(rng, spec, consent_date, subj_canonical_id)
    
    # ── Realism: Compute physiological baseline adjustments from demographics + MH ──
    realism_cfg = spec.realism
    if realism_cfg.enable_baseline_conditioning:
        mh_terms = [m.term for m in subject.medical_history]
        baseline_adj = compute_baseline_adjustments(
            age=demographics.age, sex=demographics.sex,
            race=demographics.race, medical_history_terms=mh_terms,
        )
        subject.baseline_adjustments = baseline_adj
    else:
        baseline_adj = BaselineAdjustments()
        subject.baseline_adjustments = baseline_adj
    
    # Concomitant Medications (AE-linked + MH background + standalone)
    subject.conmeds = _generate_conmeds(
        rng, spec, accepted_aes, first_dose_date, actual_end,
        subj_canonical_id, subject.medical_history,
    )
    
    # Exposure records (with dose modifications from AEs)
    subject.exposures = _generate_exposures(
        spec, armcd, treatment_sequence, first_dose_date, actual_end,
        rng=rng, adherence=latent_traits.adherence_propensity,
        subj_id=subj_canonical_id,
        ae_events=accepted_aes,
    )
    
    # Vital Signs (AR(1) dynamics, AE feedback, conditioning, missingness)
    subject.vs_records = _generate_vital_signs(
        rng, spec, treatment_sequence, first_dose_date, actual_end,
        latent_traits,
        subj_id=subj_canonical_id,
        baseline_adj=baseline_adj,
        ae_events=accepted_aes,
        adherence=latent_traits.adherence_propensity,
    )
    
    # Laboratory (AR(1) dynamics, AE feedback, conditioning, missingness, normal ranges)
    subject.lb_records = _generate_labs(
        rng, spec, treatment_sequence, first_dose_date, actual_end,
        subject.latent_traits, subj_id=subj_canonical_id,
        baseline_adj=baseline_adj,
        ae_events=accepted_aes,
        sex=demographics.sex,
        adherence=latent_traits.adherence_propensity,
    )
    
    return subject


# ─── Helper Functions ────────────────────────────────────────────────────────

def _inv_normal_approx(u: float) -> float:
    """Approximate inverse normal CDF for uniform→normal mapping."""
    import math
    # Rational approximation (Abramowitz & Stegun 26.2.23)
    u = max(1e-6, min(1 - 1e-6, u))
    t = math.sqrt(-2 * math.log(min(u, 1 - u)))
    c0, c1, c2 = 2.515517, 0.802853, 0.010328
    d1, d2, d3 = 1.432788, 0.189269, 0.001308
    result = t - (c0 + c1 * t + c2 * t * t) / (1 + d1 * t + d2 * t * t + d3 * t * t * t)
    return result if u > 0.5 else -result


def _build_treatment_sequence(spec: TrialDesignSpec, armcd: str) -> List[ArmAssignment]:
    """Build treatment_sequence for a subject.
    
    For crossover designs, armcd is a sequence code (e.g., "AB", "BAC")
    and we look up the pre-defined periods from crossover_sequences.
    For parallel designs, builds from element specs or uses single-period fallback.
    """
    # Crossover: look up sequence definition
    if spec.is_crossover and spec.crossover_sequences:
        for seq_def in spec.crossover_sequences:
            seqcd = seq_def['seqcd'] if isinstance(seq_def, dict) else seq_def.seqcd
            if seqcd == armcd:
                periods_data = seq_def['periods'] if isinstance(seq_def, dict) else seq_def.periods
                return [
                    ArmAssignment(
                        period=p['period'] if isinstance(p, dict) else p.period,
                        armcd=p['armcd'] if isinstance(p, dict) else p.armcd,
                        epoch_label=p.get('epoch', f"PERIOD {p['period']}") if isinstance(p, dict) else getattr(p, 'epoch', f"PERIOD {p.period}"),
                        start_day=p['start_day'] if isinstance(p, dict) else p.start_day,
                        end_day=p['end_day'] if isinstance(p, dict) else p.end_day,
                        washout_days_before=p.get('washout_days_before', 0) if isinstance(p, dict) else getattr(p, 'washout_days_before', 0),
                    )
                    for p in periods_data
                ]
    
    # Parallel: try element-based construction
    element_seq = spec.get_element_sequence_for_arm(armcd)
    
    treatment_periods = []
    current_day = 1
    
    for etcd in element_seq:
        elem = spec.get_element_by_etcd(etcd)
        if not elem:
            continue
        
        epoch = elem.epoch.upper()
        if epoch.startswith("TREATMENT") or epoch.startswith("PERIOD"):
            duration = elem.nominal_duration_days or 1
            treatment_periods.append(ArmAssignment(
                period=len(treatment_periods) + 1,
                armcd=armcd,
                epoch_label=epoch if epoch != "TREATMENT" else "TREATMENT",
                start_day=current_day,
                end_day=current_day + duration - 1,
            ))
        current_day += elem.nominal_duration_days or 1
    
    # Fallback: single treatment period
    if not treatment_periods:
        total = spec.compute_total_study_days()
        # Find treatment duration from elements
        treatment_dur = 0
        for elem in spec.elements:
            if elem.epoch.upper().startswith("TREATMENT"):
                treatment_dur += elem.nominal_duration_days or 0
        if treatment_dur == 0:
            treatment_dur = max(total - 28, 56)  # default
        
        treatment_periods.append(ArmAssignment(
            period=1,
            armcd=armcd,
            epoch_label="TREATMENT",
            start_day=1,
            end_day=treatment_dur,
        ))
    
    return treatment_periods


def _build_element_spans(spec: TrialDesignSpec, armcd: str) -> List[ElementSpan]:
    """Build element spans for SE domain.
    
    For crossover designs, builds from treatment_sequence periods + washouts.
    For parallel designs, builds from element path definitions.
    """
    # Crossover: build from crossover sequence periods
    if spec.is_crossover and spec.crossover_sequences:
        spans = []
        for seq_def in spec.crossover_sequences:
            seqcd = seq_def['seqcd'] if isinstance(seq_def, dict) else seq_def.seqcd
            if seqcd != armcd:
                continue
            periods_data = seq_def['periods'] if isinstance(seq_def, dict) else seq_def.periods
            prev_end = 0
            for p in periods_data:
                p_period = p['period'] if isinstance(p, dict) else p.period
                p_armcd = p['armcd'] if isinstance(p, dict) else p.armcd
                p_start = p['start_day'] if isinstance(p, dict) else p.start_day
                p_end = p['end_day'] if isinstance(p, dict) else p.end_day
                p_washout = p.get('washout_days_before', 0) if isinstance(p, dict) else getattr(p, 'washout_days_before', 0)
                p_epoch = p.get('epoch', f'PERIOD {p_period}') if isinstance(p, dict) else getattr(p, 'epoch', f'PERIOD {p_period}')
                
                # Add washout span if applicable
                if p_washout > 0 and prev_end > 0:
                    washout_start = prev_end + 1
                    washout_end = p_start - 1
                    actual_gap = washout_end - washout_start + 1
                    if actual_gap != p_washout:
                        warnings.warn(
                            f"Crossover washout mismatch for period {p_period}: "
                            f"spec says {p_washout} days but gap between periods is {actual_gap} days. "
                            f"SE element spans will use actual gap ({actual_gap}d).",
                            stacklevel=2,
                        )
                    if washout_end >= washout_start:
                        spans.append(ElementSpan(
                            element=f"Washout {p_period - 1}",
                            start_day=washout_start,
                            end_day=washout_end,
                            epoch=f"WASHOUT {p_period - 1}",
                        ))
                
                # Add treatment period span
                arm_spec = spec.get_arm_by_armcd(p_armcd)
                element_name = arm_spec.arm if arm_spec else p_armcd
                spans.append(ElementSpan(
                    element=f"Treatment Period {p_period}",
                    start_day=p_start,
                    end_day=p_end,
                    epoch=p_epoch,
                ))
                prev_end = p_end
            break
        
        if spans:
            return spans
    
    # Parallel: try element-based construction
    element_seq = spec.get_element_sequence_for_arm(armcd)
    spans = []
    current_day = 1
    
    for etcd in element_seq:
        elem = spec.get_element_by_etcd(etcd)
        if not elem:
            continue
        duration = elem.nominal_duration_days or 1
        spans.append(ElementSpan(
            element=elem.element,
            start_day=current_day,
            end_day=current_day + duration - 1,
            epoch=elem.epoch,
        ))
        current_day += duration
    
    return spans


def _generate_ae_candidates(rng: SubjectRNG, M: int, subj_id: str = "") -> List[AECandidate]:
    """Pre-draw phase: generate M candidates with stable identities (§2.2.1).
    
    P0 fix: canonical IDs are subject-scoped via subj_id prefix to prevent
    cross-subject collisions in ProvenanceMap and RELREC.
    """
    prefix = f"{subj_id}/" if subj_id else ""
    candidates = []
    for k in range(M):
        crng = rng.candidate_rng("AE", k)
        candidates.append(AECandidate(
            canonical_id=f"{prefix}AE_CAND_{k}",
            k=k,
            u_time=float(crng.random()),
            u_accept=float(crng.random()),
            u_term=float(crng.random()),
            u_severity=float(crng.random()),
            u_duration=float(crng.random()),
            u_outcome=float(crng.random()),
        ))
    return candidates


def _accept_ae_candidates(
    candidates: List[AECandidate],
    subject: CanonicalSubject,
    spec: TrialDesignSpec,
    rng: SubjectRNG,
    first_dose_date: date,
) -> List[AEEvent]:
    """Acceptance phase: select which candidates become real AEs (§2.2.1)."""
    frailty_mult = frailty_to_multiplier(subject.latent_traits.frailty_score)
    # ae_susceptibility ∈ [0,1] → multiplier ∈ [0.7, 1.3]
    ae_susc_mult = 0.7 + 0.6 * subject.latent_traits.ae_susceptibility

    total_exposure_months = subject.timeline.exposure_days / 30.0
    target_count = spec.ae_model.ae_rate_multiplier * total_exposure_months * frailty_mult * ae_susc_mult
    
    # Exposure-aware acceptance rate using shaped exposure probability
    P_exp = shaped_exposure_probability(spec, subject.treatment_sequence, subject.timeline.total_study_days)
    p_accept = min(target_count / (len(candidates) * P_exp), 1.0) if candidates else 0
    
    if p_accept >= 1.0:
        warnings.warn(
            f"AE pool near exhaustion: p_accept={p_accept:.2f} "
            f"for {subject.identity.canonical_id}"
        )
    
    # Build AE term library for mapping
    ae_terms = _get_ae_term_library(spec)
    total_weight = sum(t['weight'] for t in ae_terms)
    
    accepted = []
    total_study_days = subject.timeline.total_study_days
    
    for c in candidates:
        # Step 1: Bernoulli acceptance
        if c.u_accept >= p_accept:
            continue
        
        # Step 2: Apply Beta-PPF time shaping, then map to absolute study day (1-based, Contract 6)
        u_shaped = _apply_time_shaping(c.u_time, spec)
        absolute_day = 1 + int(u_shaped * total_study_days)
        absolute_day = max(1, min(absolute_day, total_study_days))
        
        # Step 3: Check if day falls in active treatment period
        period = _find_period_for_day(absolute_day, subject.treatment_sequence)
        if period is None:
            continue
        
        # Step 4: Map to actual onset date
        onset_date = first_dose_date + timedelta(days=absolute_day - 1)
        
        # Step 5: CDF-map attributes
        term_info = _map_term(c.u_term, ae_terms, total_weight)
        severity = _map_severity(c.u_severity, subject.latent_traits)
        duration = _map_duration(c.u_duration, severity)
        outcome = _map_outcome(c.u_outcome, severity, spec)
        
        is_fatal = outcome == "FATAL"
        is_serious = severity == "SEVERE" or is_fatal
        
        # Determine relationship and action from separate draws
        rel_u = rng.draw("AE", "rel", c.k, RNGComponent.RELATIONSHIP)[0]
        relationship = _map_from_dist(rel_u, spec.ae_model.relationship_dist)
        
        action_u = rng.draw("AE", "action", c.k, RNGComponent.ACTION)[0]
        action = _map_action(action_u, relationship, severity)
        
        accepted.append(AEEvent(
            canonical_id=c.canonical_id,
            period=period.period,
            onset_date=onset_date,
            term=term_info['term'],
            decoded_term=term_info['decoded'],
            body_system=term_info['bodsys'],
            severity=severity,
            duration_days=duration,
            outcome=outcome,
            is_serious=is_serious,
            is_fatal=is_fatal,
            relationship=relationship,
            action=action,
            # MedDRA hierarchy (Phase 2)
            pt_code=term_info.get('pt_code', 0),
            hlt_name=term_info.get('hlt_name', ''),
            hlt_code=term_info.get('hlt_code', 0),
            hlgt_name=term_info.get('hlgt_name', ''),
            hlgt_code=term_info.get('hlgt_code', 0),
            soc_name=term_info.get('soc_name', term_info.get('bodsys', '')),
            soc_code=term_info.get('soc_code', 0),
        ))
    
    return accepted


def _find_period_for_day(absolute_day: int, treatment_sequence: List[ArmAssignment]) -> Optional[ArmAssignment]:
    """Map a 1-based absolute study day to the active treatment period."""
    for period in treatment_sequence:
        if period.start_day <= absolute_day <= period.end_day:
            return period
    return None


def _get_ae_term_library(spec: TrialDesignSpec) -> List[Dict]:
    """Get AE term library from spec, MedDRA library, or defaults.
    
    Enriches spec-defined terms with MedDRA hierarchy data via lookup
    against CORE_MEDDRA_TERMS when available (Phase 2 §3.1).
    """
    # Build lookup index: normalized PT name → MedDRATerm
    all_terms = get_all_meddra_terms()
    meddra_lookup = {}
    for mdt in all_terms:
        meddra_lookup[mdt.pt_name.upper()] = mdt
    
    def _enrich_with_meddra(term_dict: Dict) -> Dict:
        """Add MedDRA hierarchy fields if term matches core library."""
        name = term_dict.get('decoded', term_dict.get('term', '')).upper()
        # Normalize common spelling differences (US vs MedDRA spellings)
        name_variants = [
            name,
            name.replace('DIARRHEA', 'DIARRHOEA'),
            name.replace('HAEMORRHAGE', 'HEMORRHAGE'),
            name.replace('HEMORRHAGE', 'HAEMORRHAGE'),
            name.replace('ANAEMIA', 'ANEMIA'),
            name.replace('ANEMIA', 'ANAEMIA'),
            name.replace('HAEMOLYSIS', 'HEMOLYSIS'),
            name.replace('HEMOLYSIS', 'HAEMOLYSIS'),
            name.replace('FLARE', ''),  # "ULCERATIVE COLITIS FLARE" → "ULCERATIVE COLITIS"
        ]
        name_variants = [v.strip() for v in name_variants if v.strip()]
        for variant in name_variants:
            if variant in meddra_lookup:
                mdt = meddra_lookup[variant]
                term_dict['pt_code'] = mdt.pt_code
                term_dict['hlt_name'] = mdt.hlt_name
                term_dict['hlt_code'] = mdt.hlt_code
                term_dict['hlgt_name'] = mdt.hlgt_name
                term_dict['hlgt_code'] = mdt.hlgt_code
                term_dict['soc_name'] = mdt.soc_name
                term_dict['soc_code'] = mdt.soc_code
                if not term_dict.get('can_be_fatal'):
                    term_dict['can_be_fatal'] = mdt.can_be_fatal
                return term_dict
        # No match — set defaults for unknown terms
        term_dict.setdefault('pt_code', 0)
        term_dict.setdefault('hlt_name', '')
        term_dict.setdefault('hlt_code', 0)
        term_dict.setdefault('hlgt_name', '')
        term_dict.setdefault('hlgt_code', 0)
        term_dict.setdefault('soc_name', term_dict.get('bodsys', ''))
        term_dict.setdefault('soc_code', 0)
        return term_dict

    if spec.ae_model.ae_term_library:
        terms = []
        for t in spec.ae_model.ae_term_library:
            td = {
                'term': t.aeterm, 'decoded': t.aedecod,
                'bodsys': t.aebodsys, 'weight': t.weight,
            }
            terms.append(_enrich_with_meddra(td))
        # Add serious/fatal AEs from MedDRA library
        for mdt in CORE_MEDDRA_TERMS:
            if mdt.can_be_fatal:
                terms.append(meddra_term_to_dict(mdt))
        return terms
    
    # Try protocol-specific MedDRA terms
    proto_key = _detect_protocol_key(spec)
    if proto_key and proto_key in PROTOCOL_TERM_LIBRARIES:
        terms = [meddra_term_to_dict(t) for t in PROTOCOL_TERM_LIBRARIES[proto_key]]
        # Add serious/fatal terms
        for mdt in CORE_MEDDRA_TERMS:
            if mdt.can_be_fatal and mdt.pt_name.upper() not in {t['term'] for t in terms}:
                terms.append(meddra_term_to_dict(mdt))
        return terms
    
    return DEFAULT_AE_TERMS


def _detect_protocol_key(spec: TrialDesignSpec) -> Optional[str]:
    """Detect protocol key from study_id for MedDRA term selection."""
    sid = spec.study_id.upper()
    mappings = {
        'AV005': 'bda', 'TYREE': 'bda',
        'P261': 'usl261', 'USL261': 'usl261',
        'KVD900': 'konfident', 'KONFIDENT': 'konfident',
    }
    for key, proto in mappings.items():
        if key in sid:
            return proto
    return None


def _map_term(u: float, terms: List[Dict], total_weight: float) -> Dict:
    """Map uniform to AE term via CDF."""
    cumulative = 0.0
    for t in terms:
        cumulative += t['weight'] / total_weight
        if u < cumulative:
            return t
    return terms[-1]


def _map_severity(u: float, traits: LatentTraits) -> str:
    """Map uniform to severity via frailty-shifted CDF (Contract 5)."""
    mild_t = mild_threshold(traits.frailty_score)
    mod_t = moderate_threshold(traits.frailty_score)
    if u < mild_t:
        return "MILD"
    elif u < mod_t:
        return "MODERATE"
    else:
        return "SEVERE"


def _map_duration(u: float, severity: str) -> int:
    """Map uniform to AE duration in days."""
    if severity == "SEVERE":
        return 1 + int(u * 60)
    elif severity == "MODERATE":
        return 1 + int(u * 30)
    else:
        return 1 + int(u * 14)


def _map_outcome(u: float, severity: str, spec: TrialDesignSpec) -> str:
    """Map uniform to outcome.
    
    P1 fix: When enable_fatal is True, inject FATAL into outcome_dist
    using death_rate, renormalizing the rest. This ensures fatal AEs
    are actually generated when the knob is turned on.
    """
    dist = spec.ae_model.outcome_dist.copy()
    
    if spec.ae_model.enable_fatal:
        # P1 fix: inject FATAL at death_rate, but only for SEVERE AEs
        # to maintain clinical plausibility
        if severity == "SEVERE" and 'FATAL' not in dist:
            death_rate = spec.ae_model.death_rate
            # Scale down existing probabilities to make room for FATAL
            scale = 1.0 - death_rate
            dist = {k: v * scale for k, v in dist.items()}
            dist['FATAL'] = death_rate
        elif severity != "SEVERE" and 'FATAL' in dist:
            # Non-severe AEs should not be fatal
            del dist['FATAL']
    else:
        # Remove FATAL if present but not enabled
        if 'FATAL' in dist:
            del dist['FATAL']
    
    total = sum(dist.values())
    if total == 0:
        return "RECOVERED/RESOLVED"
    return _map_from_dist(u, dist)


def _map_from_dist(u: float, dist: Dict[str, float]) -> str:
    """Map uniform to categorical from distribution dict."""
    total = sum(dist.values())
    cumulative = 0.0
    for k, v in dist.items():
        cumulative += v / total
        if u < cumulative:
            return k
    return list(dist.keys())[-1]


def _map_action(u: float, relationship: str, severity: str) -> str:
    """Map uniform to action based on relationship and severity."""
    if relationship in ['NOT RELATED', 'UNLIKELY RELATED']:
        return 'DOSE NOT CHANGED'
    if severity == 'SEVERE':
        actions = ['DRUG INTERRUPTED', 'DOSE REDUCED', 'DRUG WITHDRAWN']
    elif severity == 'MODERATE':
        actions = ['DRUG INTERRUPTED', 'DOSE REDUCED', 'DOSE NOT CHANGED']
    else:
        actions = ['DOSE NOT CHANGED', 'DOSE REDUCED']
    idx = int(u * len(actions))
    return actions[min(idx, len(actions) - 1)]


def _derive_disposition(
    aes: List[AEEvent],
    subject: CanonicalSubject,
    spec: TrialDesignSpec,
    rng: SubjectRNG,
    first_dose_date: date,
    planned_end: date,
) -> Tuple[SubjectDisposition, Optional[SubjectDeath]]:
    """Stage 3: Derive disposition from accepted AEs.
    
    Latent trait wiring (Contract 5):
    - frailty_score → dropout probability via dropout_multiplier()
    - Higher frailty = more likely to drop out (multiplier in [0.6, 1.4])
    """
    death = None
    
    # Check for fatal AEs
    fatal_aes = [ae for ae in aes if ae.is_fatal]
    if fatal_aes:
        # Earliest fatal AE determines death
        fatal_ae = min(fatal_aes, key=lambda a: a.onset_date)
        death_delay = rng.draw_int("disposition", RNGComponent.DEATH_DELAY, low=0, high=3)
        death_date = fatal_ae.onset_date + timedelta(days=death_delay)
        
        death = SubjectDeath(date=death_date, linked_ae_id=fatal_ae.canonical_id)
        
        return SubjectDisposition(
            outcome="DEATH",
            date=death_date,
            reason="DEATH",
            linked_ae_id=fatal_ae.canonical_id,
        ), death
    
    # Check for withdrawal AEs
    withdrawal_aes = [ae for ae in aes if ae.action == "DRUG WITHDRAWN"]
    if withdrawal_aes:
        withdrawal_ae = min(withdrawal_aes, key=lambda a: a.onset_date)
        return SubjectDisposition(
            outcome="ADVERSE EVENT",
            date=withdrawal_ae.onset_date,
            reason="ADVERSE EVENT",
            linked_ae_id=withdrawal_ae.canonical_id,
        ), None
    
    # Check for general dropout — frailty-modulated (Contract 5)
    dropout_u = rng.draw("disposition", RNGComponent.DROPOUT)[0]
    disp = spec.disposition_model
    
    # Frailty-adjusted completion rate:
    # dropout_multiplier maps frailty [0,1] → [0.6, 1.4]
    # Higher frailty → higher multiplier → lower effective completion rate
    frailty = subject.latent_traits.frailty_score
    dropout_mult = dropout_multiplier(frailty)
    # base_dropout_rate = 1 - completion_rate; adjusted = base * multiplier
    base_dropout_rate = 1.0 - disp.completion_rate
    adjusted_dropout_rate = min(base_dropout_rate * dropout_mult, 0.95)
    
    if dropout_u < adjusted_dropout_rate:
        # Subject drops out — use Weibull timing if enabled (front-loaded)
        total_days = (planned_end - first_dose_date).days
        realism_cfg = spec.realism
        if realism_cfg.enable_weibull_dropout and total_days > 1:
            weibull_u = rng.draw("disposition", RNGComponent.DROPOUT_DAY)[0]
            dropout_day = weibull_dropout_day(
                weibull_u, total_days, shape=realism_cfg.dropout_weibull_shape
            )
        else:
            dropout_day = rng.draw_int("disposition", RNGComponent.DROPOUT_DAY, low=1, high=max(total_days, 1))
        dropout_date = first_dose_date + timedelta(days=dropout_day)
        
        reasons = [c for c in disp.ds_categories if c != "COMPLETED" and c != "DEATH"]
        if not reasons:
            reasons = ["WITHDRAWAL BY SUBJECT"]
        dropout_reason = rng.draw_choice(
            "disposition", RNGComponent.DROPOUT_REASON,
            items=reasons
        )
        
        return SubjectDisposition(
            outcome=dropout_reason,
            date=dropout_date,
            reason=dropout_reason,
        ), None
    
    # Completed
    return SubjectDisposition(
        outcome="COMPLETED",
        date=planned_end,
        reason="COMPLETED",
    ), None


def _generate_medical_history(
    rng: SubjectRNG, spec: TrialDesignSpec, consent_date: date,
    subj_id: str = "",
) -> List[MHEvent]:
    """Generate MH events keyed per condition.
    
    Realism enhancements:
    - Partial dates for start dates (ISO 8601 year-month)
    - Age-dependent condition count via baseline_adjustments
    """
    prefix = f"{subj_id}/" if subj_id else ""
    mh_model = spec.mh_model
    if not mh_model.generate_mh:
        return []
    
    conditions = mh_model.condition_library if mh_model.condition_library else DEFAULT_MH_CONDITIONS
    
    # How many conditions
    n_conditions = rng.draw_int("MH", RNGComponent.N_CONDITIONS,
                                low=mh_model.n_conditions_min,
                                high=min(mh_model.n_conditions_max, len(conditions)))
    
    realism_cfg = spec.realism
    events = []
    selected_indices = set()
    for k in range(n_conditions):
        # Select condition (avoid duplicates)
        u_cond = rng.draw("MH", k, RNGComponent.CONDITION)[0]
        idx = int(u_cond * len(conditions))
        idx = min(idx, len(conditions) - 1)
        # Skip duplicates by advancing to next available
        attempts = 0
        while idx in selected_indices and attempts < len(conditions):
            idx = (idx + 1) % len(conditions)
            attempts += 1
        if attempts >= len(conditions):
            continue
        selected_indices.add(idx)
        cond = conditions[idx]
        
        cond_term = cond.mhterm if hasattr(cond, 'mhterm') else cond.get('term', cond.get('mhterm', ''))
        cond_cat = cond.mhcat if hasattr(cond, 'mhcat') else cond.get('cat', cond.get('mhcat', 'GENERAL'))
        
        # Start date
        years_back = rng.draw_int("MH", k, RNGComponent.MH_START, low=1, high=mh_model.capture_window_years)
        start = consent_date - timedelta(days=years_back * 365)
        
        # Partial date for MH start (common in real data)
        start_date_partial = ""
        if realism_cfg.enable_partial_dates:
            partial_u = rng.draw("MH", k, RNGComponent.PARTIAL_DATE)[0]
            start_date_partial = maybe_partial_date(
                start, partial_u, partial_rate=realism_cfg.mh_partial_date_rate
            )
        
        # Ongoing?
        is_ongoing = rng.draw("MH", k, RNGComponent.ONGOING)[0] < 0.4
        end = None if is_ongoing else consent_date - timedelta(
            days=rng.draw_int("MH", k, RNGComponent.MH_END, low=30, high=years_back * 365)
        )
        
        events.append(MHEvent(
            canonical_id=f"{prefix}MH_{k}",
            term=cond_term,
            category=cond_cat,
            start_date=start,
            end_date=end,
            is_ongoing=is_ongoing,
            start_date_partial=start_date_partial,
        ))
    
    return events


def _generate_conmeds(
    rng: SubjectRNG, spec: TrialDesignSpec,
    aes: List[AEEvent], first_dose: date, end_date: date,
    subj_id: str = "",
    medical_history: Optional[List[MHEvent]] = None,
) -> List[CMEvent]:
    """Generate CM events: MH-linked background + AE-linked treatment + standalone.
    
    Realism enhancements:
    - MH → CM: ongoing conditions get pharmacologically appropriate background meds
    - AE → CM: uses AE_TO_CM_MAP for indication-appropriate treatment selection
    - Standalone CMs from spec library as before (reduced count)
    """
    prefix = f"{subj_id}/" if subj_id else ""
    events = []
    ordinal = 0
    realism_cfg = spec.realism
    
    # ── MH-linked background CMs (new) ──
    if realism_cfg.enable_mh_background_cm and medical_history:
        for mh_idx, mh in enumerate(medical_history):
            if not mh.is_ongoing:
                continue
            u_select = rng.draw("CM", "mh_bg", mh_idx, RNGComponent.MH_BG_CM_SELECT)[0]
            # ~70% chance an ongoing condition has a background med
            if u_select > 0.70:
                continue
            cm_info = get_background_cm_for_mh(mh.term, u_select / 0.70)
            if cm_info is None:
                continue
            events.append(CMEvent(
                canonical_id=f"{prefix}CM_MHBG_{mh_idx}",
                treatment=cm_info['cmtrt'],
                decoded=cm_info['cmtrt'],
                category="PRIOR",
                dose=cm_info.get('dose', 0),
                dose_unit=cm_info.get('unit', 'mg'),
                frequency=cm_info.get('freq', 'QD'),
                route=cm_info.get('route', 'ORAL'),
                indication=mh.term,
                start_date=mh.start_date,  # ongoing from before consent
                end_date=end_date,          # continues through study
                linked_mh_term=mh.term,
            ))
            ordinal += 1
    
    # ── AE-linked CMs (pharmacologically appropriate) ──
    for ae in aes:
        if ae.severity in ("MODERATE", "SEVERE") and ae.outcome != "FATAL":
            cm_u = rng.draw("CM", ae.canonical_id, RNGComponent.CM_SELECTION)[0]
            if cm_u < 0.6:  # 60% chance of CM for moderate/severe AE
                if realism_cfg.enable_pharmacological_cm:
                    # Use pharmacological mapping
                    select_u = rng.draw("CM", ae.canonical_id, RNGComponent.AE_CM_SELECT)[0]
                    ae_term = (ae.decoded_term or ae.term).strip()
                    cm_info = get_cm_for_ae(ae_term, select_u)
                    if cm_info is None:
                        continue
                    cm_trt = cm_info['cmtrt']
                    cm_route = cm_info.get('route', 'ORAL')
                    cm_freq = cm_info.get('freq', 'PRN')
                    cm_dose = cm_info.get('dose', 0)
                    cm_unit = cm_info.get('unit', 'mg')
                else:
                    # Legacy: random selection from library
                    cm_lib = spec.cm_model.cm_library if spec.cm_model.cm_library else DEFAULT_CM_LIBRARY
                    cm_idx = int(rng.draw("CM", ae.canonical_id, RNGComponent.TERM)[0] * len(cm_lib))
                    cm_idx = min(cm_idx, len(cm_lib) - 1)
                    cm_info = cm_lib[cm_idx]
                    cm_trt = cm_info.get('cmtrt', cm_info.get('treatment', 'UNKNOWN'))
                    cm_route = cm_info.get('cmroute', 'ORAL')
                    cm_freq = cm_info.get('cmdosfrq', 'PRN')
                    cm_dose = 0
                    cm_unit = 'mg'
                
                dur = rng.draw_int("CM", ae.canonical_id, RNGComponent.CM_DURATION, low=3, high=30)
                
                events.append(CMEvent(
                    canonical_id=f"{prefix}CM_{ae.canonical_id.split('/')[-1]}_{ordinal}",
                    treatment=cm_trt,
                    decoded=cm_trt,
                    category="CONCOMITANT",
                    dose=cm_dose,
                    dose_unit=cm_unit,
                    frequency=cm_freq,
                    route=cm_route,
                    indication=ae.term,
                    start_date=ae.onset_date,
                    end_date=ae.onset_date + timedelta(days=dur),
                    linked_ae_id=ae.canonical_id,
                ))
                ordinal += 1
    
    # ── Standalone CMs (reduced count since MH background covers most) ──
    max_standalone = 1 if (realism_cfg.enable_mh_background_cm and medical_history) else 3
    n_standalone = rng.draw_int("CM", RNGComponent.CM_COUNT, low=0, high=max_standalone)
    cm_lib = spec.cm_model.cm_library if spec.cm_model.cm_library else DEFAULT_CM_LIBRARY
    for k in range(n_standalone):
        cm_idx = int(rng.draw("CM", "standalone", k, RNGComponent.TERM)[0] * len(cm_lib))
        cm_idx = min(cm_idx, len(cm_lib) - 1)
        cm_info = cm_lib[cm_idx]
        
        cm_trt = cm_info.get('cmtrt', cm_info.get('treatment', 'UNKNOWN'))
        cm_route = cm_info.get('cmroute', 'ORAL')
        cm_freq = cm_info.get('cmdosfrq', 'PRN')
        
        start_offset = rng.draw_int("CM", "standalone", k, RNGComponent.START_DATE, low=0, high=max((end_date - first_dose).days, 1))
        cm_start = first_dose + timedelta(days=start_offset)
        dur = rng.draw_int("CM", "standalone", k, RNGComponent.CM_DURATION, low=7, high=90)
        cm_end = min(cm_start + timedelta(days=dur), end_date)
        
        events.append(CMEvent(
            canonical_id=f"{prefix}CM_STANDALONE_{k}",
            treatment=cm_trt,
            decoded=cm_trt,
            category="CONCOMITANT",
            frequency=cm_freq,
            route=cm_route,
            start_date=cm_start,
            end_date=cm_end,
        ))
    
    return events


def _generate_exposures(
    spec: TrialDesignSpec, armcd: str,
    treatment_sequence: List[ArmAssignment],
    first_dose_date: date, actual_end: date,
    rng: SubjectRNG = None,
    adherence: float = 1.0,
    subj_id: str = "",
    ae_events: Optional[List[AEEvent]] = None,
) -> List[EXEvent]:
    """Generate EX records per period.
    
    Latent trait wiring (Contract 5):
    - adherence_propensity → EX end date shortening
    - Low adherence subjects have treatment periods cut short
    - adherence=1.0 → full dosing; adherence=0.0 → ~40% of planned duration
    
    Realism enhancements:
    - AE with DRUG INTERRUPTED → split EX record with gap
    - AE with DOSE REDUCED → subsequent EX at reduced dose
    
    For crossover: each period has its own treatment (from ArmAssignment.armcd).
    For parallel: all periods use the same arm's regimen.
    """
    prefix = f"{subj_id}/" if subj_id else ""
    events = []
    realism_cfg = spec.realism
    
    for period in treatment_sequence:
        # For crossover, look up the regimen by the period's armcd
        period_armcd = period.armcd
        arm_spec = spec.get_arm_by_armcd(period_armcd)
        
        if not arm_spec or not arm_spec.regimen:
            # Fallback for crossover: try original armcd 
            arm_spec = spec.get_arm_by_armcd(armcd)
            if not arm_spec or not arm_spec.regimen:
                continue
        
        for reg_idx, reg in enumerate(arm_spec.regimen):
            ex_start = first_dose_date + timedelta(days=period.start_day - 1)
            ex_end = first_dose_date + timedelta(days=period.end_day - 1)
            ex_end = min(ex_end, actual_end)
            
            if ex_start > actual_end:
                continue
            
            # Adherence-modulated end date
            if rng is not None and adherence < 0.95:
                planned_duration = (ex_end - ex_start).days
                if planned_duration > 1:
                    keep_frac = 0.4 + 0.6 * adherence
                    jitter_u = rng.draw("EX", period.period, reg_idx, "adherence_jitter")[0]
                    jittered = keep_frac + (jitter_u - 0.5) * 0.2
                    jittered = max(0.3, min(1.0, jittered))
                    adherent_days = max(1, int(planned_duration * jittered))
                    ex_end = ex_start + timedelta(days=adherent_days)
                    ex_end = min(ex_end, actual_end)
            
            # ── Realism: Dose modifications from AEs ──
            if realism_cfg.enable_ex_dose_modifications and ae_events:
                dose_mods = derive_dose_modifications(ae_events, ex_start, ex_end)
                
                if dose_mods:
                    # Split EX records around dose modifications
                    current_start = ex_start
                    current_dose = reg.dose
                    seg_idx = 0
                    
                    for mod in dose_mods:
                        if mod.modification_date <= current_start:
                            # Modification before current segment start
                            if mod.action == "REDUCED":
                                current_dose = reg.dose * mod.dose_reduction_fraction
                            continue
                        
                        # Emit segment before modification
                        if current_start < mod.modification_date:
                            events.append(EXEvent(
                                canonical_id=f"{prefix}EX_{period.period}_{period.start_day}_{reg_idx}_s{seg_idx}",
                                period=period.period,
                                treatment=reg.extrt,
                                dose=current_dose,
                                dose_unit=reg.dose_unit,
                                form=getattr(reg, 'dosage_form', ''),
                                frequency=reg.frequency.value if hasattr(reg.frequency, 'value') else str(reg.frequency),
                                route=reg.route.value if hasattr(reg.route, 'value') else str(reg.route),
                                start_date=current_start,
                                end_date=mod.modification_date - timedelta(days=1),
                            ))
                            seg_idx += 1
                        
                        if mod.action == "INTERRUPTED":
                            # Gap in dosing
                            current_start = mod.modification_date + timedelta(days=mod.interruption_days)
                            if current_start > ex_end:
                                current_start = ex_end + timedelta(days=1)  # will skip final segment
                        elif mod.action == "REDUCED":
                            current_dose = reg.dose * mod.dose_reduction_fraction
                            current_start = mod.modification_date
                    
                    # Emit final segment
                    if current_start <= ex_end:
                        events.append(EXEvent(
                            canonical_id=f"{prefix}EX_{period.period}_{period.start_day}_{reg_idx}_s{seg_idx}",
                            period=period.period,
                            treatment=reg.extrt,
                            dose=current_dose,
                            dose_unit=reg.dose_unit,
                            form=getattr(reg, 'dosage_form', ''),
                            frequency=reg.frequency.value if hasattr(reg.frequency, 'value') else str(reg.frequency),
                            route=reg.route.value if hasattr(reg.route, 'value') else str(reg.route),
                            start_date=current_start,
                            end_date=ex_end,
                        ))
                    continue  # skip the default append below
            
            # Default: single EX record for this period/regimen
            events.append(EXEvent(
                canonical_id=f"{prefix}EX_{period.period}_{period.start_day}_{reg_idx}",
                period=period.period,
                treatment=reg.extrt,
                dose=reg.dose,
                dose_unit=reg.dose_unit,
                form=getattr(reg, 'dosage_form', ''),
                frequency=reg.frequency.value if hasattr(reg.frequency, 'value') else str(reg.frequency),
                route=reg.route.value if hasattr(reg.route, 'value') else str(reg.route),
                start_date=ex_start,
                end_date=ex_end,
            ))
    
    return events


# ─── Phase 2: Beta-PPF Time Shaping ──────────────────────────────────────────

def shaped_exposure_probability(
    spec: TrialDesignSpec,
    treatment_sequence: List[ArmAssignment],
    total_study_days: int,
) -> float:
    """Probability that a Beta-shaped time lands in an active treatment period.
    
    Uses cached P_exp from spec.ae_model.p_exp_by_sequence when available
    (set at spec-resolution time by _finalize_spec, Contract 4).
    Falls back to runtime computation only for test specs without caching.
    """
    # Check cache first (Contract 4: no SciPy CDF in hot loop)
    if spec.ae_model.p_exp_by_sequence and treatment_sequence:
        # Look up by armcd of first period (parallel) or sequence code
        armcd = treatment_sequence[0].armcd
        if armcd in spec.ae_model.p_exp_by_sequence:
            return spec.ae_model.p_exp_by_sequence[armcd]
        # For crossover, try sequence code from subject's arm_code
        if spec.ae_model.min_p_exp is not None:
            # Use min_p_exp as conservative fallback
            return spec.ae_model.min_p_exp
    
    # Fallback: runtime computation (for test fixtures without _finalize_spec)
    a, b = spec.ae_model.time_shape_params
    
    if total_study_days <= 0:
        return 1e-6
    
    if a == 1.0 and b == 1.0:
        exposure_days = sum(p.end_day - p.start_day + 1 for p in treatment_sequence)
        return max(exposure_days / total_study_days, 1e-6)
    
    if not HAS_SCIPY:
        exposure_days = sum(p.end_day - p.start_day + 1 for p in treatment_sequence)
        return max(exposure_days / total_study_days, 1e-6)
    
    p = 0.0
    for period in treatment_sequence:
        lo = (period.start_day - 1) / total_study_days
        hi = period.end_day / total_study_days
        p += beta_dist.cdf(hi, a, b) - beta_dist.cdf(lo, a, b)
    
    return max(p, 1e-6)


# ─── Beta PPF LUT Cache ─────────────────────────────────────────────────────
# Precomputed once per unique (a, b) pair. Deterministic LUT with linear
# interpolation replaces scipy.stats.beta.ppf() calls in the hot loop.
# At N=44k, M~100-500 this avoids millions of expensive PPF evaluations.

_BETA_PPF_LUT_SIZE = 2048
_BETA_PPF_CACHE: dict = {}  # (a, b) → np.ndarray of shape (_BETA_PPF_LUT_SIZE+1,)


def _get_beta_ppf_lut(a: float, b: float) -> np.ndarray:
    """Get or compute a Beta PPF lookup table for parameters (a, b)."""
    key = (a, b)
    if key not in _BETA_PPF_CACHE:
        if not HAS_SCIPY:
            # No scipy: uniform passthrough (identity LUT)
            _BETA_PPF_CACHE[key] = np.linspace(0.0, 1.0, _BETA_PPF_LUT_SIZE + 1)
        else:
            import numpy as np
            # Uniform quantiles in (0, 1), avoiding exact 0 and 1
            u = np.linspace(1e-8, 1.0 - 1e-8, _BETA_PPF_LUT_SIZE + 1)
            lut = beta_dist.ppf(u, a, b).astype(np.float64)
            # Guard NaN at tails
            lut = np.clip(np.nan_to_num(lut, nan=0.0), 0.0, 1.0 - 1e-10)
            _BETA_PPF_CACHE[key] = lut
    return _BETA_PPF_CACHE[key]


def _apply_time_shaping(u_time: float, spec: TrialDesignSpec) -> float:
    """Apply Beta-PPF time shaping for early/late AE clustering (§2.2.1).
    
    Uses precomputed LUT with linear interpolation for performance.
    Returns a value in [0, 1) that replaces the raw uniform for day mapping.
    """
    a, b = spec.ae_model.time_shape_params
    if a == 1.0 and b == 1.0:
        return u_time  # no shaping (uniform)
    
    lut = _get_beta_ppf_lut(a, b)
    n = len(lut) - 1  # _BETA_PPF_LUT_SIZE
    
    # Linear interpolation into LUT
    u_clamped = max(0.0, min(1.0 - 1e-10, u_time))
    pos = u_clamped * n
    idx = int(pos)
    frac = pos - idx
    
    if idx >= n:
        return float(lut[n])
    
    result = lut[idx] * (1.0 - frac) + lut[idx + 1] * frac
    return min(max(float(result), 0.0), 1.0 - 1e-10)


# ─── Phase 2: Crossover Helpers ──────────────────────────────────────────────

def _get_crossover_label(spec: TrialDesignSpec, seqcd: str) -> str:
    """Get human-readable label for a crossover sequence."""
    for seq_def in spec.crossover_sequences:
        code = seq_def['seqcd'] if isinstance(seq_def, dict) else seq_def.seqcd
        if code == seqcd:
            label = seq_def.get('label', None) if isinstance(seq_def, dict) else getattr(seq_def, 'label', None)
            if label:
                return label
    return f"Sequence {seqcd}"


# ─── Phase 2: VS/LB Generation (record-keyed RNG) ────────────────────────────

def _generate_vital_signs(
    rng: SubjectRNG,
    spec: TrialDesignSpec,
    treatment_sequence: List[ArmAssignment],
    first_dose_date: date,
    actual_end: date,
    latent_traits: LatentTraits,
    subj_id: str = "",
    baseline_adj: Optional['BaselineAdjustments'] = None,
    ae_events: Optional[List[AEEvent]] = None,
    adherence: float = 1.0,
) -> List[VSRecord]:
    """Generate VS records with realistic dynamics.
    
    Realism enhancements:
    - Baseline conditioning from demographics + MH
    - AR(1) autocorrelation (consecutive similar values)
    - AE → VS perturbations (e.g., Hypertension AE → elevated BP)
    - Visit attendance missingness
    - Assessment-level missingness
    """
    prefix = f"{subj_id}/" if subj_id else ""
    records = []
    vs_tests = spec.vs_model.tests
    realism_cfg = spec.realism
    if baseline_adj is None:
        baseline_adj = BaselineAdjustments()
    if ae_events is None:
        ae_events = []
    
    # Get visits relevant to VS collection
    vs_visits = _get_measurement_visits(spec, treatment_sequence, first_dose_date, actual_end, rng)
    total_visits = len(vs_visits)
    
    # Generate conditioned baseline values
    baselines = {}
    for test_item in vs_tests:
        adj = baseline_adj.vs_adjustments.get(test_item.testcd, 0.0)
        bl_val = rng.draw_normal("VS", "baseline", test_item.testcd,
                                 mean=test_item.baseline_mean + adj,
                                 std=test_item.baseline_sd)
        bl_val = max(test_item.plausible_min, min(test_item.plausible_max, bl_val))
        baselines[test_item.testcd] = bl_val
    
    # AR(1) state per test — test-specific rho for realistic autocorrelation
    ar_state = {t.testcd: 0.0 for t in vs_tests}
    default_rho = realism_cfg.ar1_rho_vs if realism_cfg.enable_ar1_dynamics else 0.0
    noise_scale = realism_cfg.vs_noise_scale

    # Subject-specific trend scaling: frailty modulates treatment response
    trend_scale = 0.7 + 0.6 * latent_traits.frailty_score if hasattr(latent_traits, 'frailty_score') else 1.0

    for v_idx, visit_info in enumerate(vs_visits):
        period = visit_info['period']
        visitnum = visit_info['visitnum']
        visit_label = visit_info['label']
        visit_date = visit_info['date']
        study_day = visit_info.get('study_day', None)

        if visit_date > actual_end:
            continue

        # Visit-level missingness
        if realism_cfg.enable_missingness and total_visits > 2:
            miss_u = rng.draw("VS", "visit_miss", v_idx, RNGComponent.VISIT_ATTEND)[0]
            visit_frac = v_idx / max(total_visits - 1, 1)
            if should_miss_visit(miss_u, realism_cfg.visit_miss_rate, visit_frac, adherence):
                continue  # entire visit missed

        # AE perturbations for this visit
        ae_perturbs = compute_ae_perturbations(ae_events, visit_date) if realism_cfg.enable_ae_feedback else {}

        # Shared BP noise component: SYSBP and DIABP are correlated (~0.7)
        bp_shared_draw = rng.draw_normal("VS", period, visitnum, "BP_SHARED", RNGComponent.VALUE,
                                          mean=0.0, std=1.0)
        bp_share_weight = 0.6  # fraction of noise from shared BP component

        visit_values = {}  # track values for derived records (BMI)

        for test_item in vs_tests:
            tc = test_item.testcd

            # Assessment-level missingness
            if realism_cfg.enable_missingness:
                assess_u = rng.draw("VS", "assess_miss", v_idx, tc, RNGComponent.ASSESS_MISS_VS)[0]
                if should_miss_assessment(assess_u, realism_cfg.vs_assessment_miss_rate):
                    records.append(VSRecord(
                        canonical_id=f"{prefix}VS_{period}_{int(visitnum)}_{tc}",
                        period=period, visitnum=visitnum, visit_label=visit_label,
                        testcd=tc, test=test_item.test, value=0.0,
                        unit=test_item.unit, visit_date=visit_date,
                        study_day=study_day, is_missing=True,
                    ))
                    continue

            # Record-keyed draw
            noise_draw = rng.draw_normal("VS", period, visitnum, tc, RNGComponent.VALUE,
                                          mean=0.0, std=1.0)

            # BP correlation: mix shared and individual noise for SYSBP/DIABP
            if tc in ('SYSBP', 'DIABP'):
                noise_draw = bp_share_weight * bp_shared_draw + (1.0 - bp_share_weight) * noise_draw

            rho = get_ar1_rho(tc, default_rho) if realism_cfg.enable_ar1_dynamics else 0.0
            if realism_cfg.enable_ar1_dynamics:
                ar_state[tc] = ar1_next_state(
                    ar_state[tc], rho,
                    test_item.baseline_sd * noise_scale, noise_draw
                )
                noise = ar_state[tc]
            else:
                noise = noise_draw * test_item.baseline_sd * 0.15

            # Trend — subject-specific scaling via frailty
            days_on_study = (visit_date - first_dose_date).days if visit_date >= first_dose_date else 0
            trend = test_item.trend_slope * trend_scale * days_on_study / 30.0

            # AE feedback perturbation
            ae_shift = ae_perturbs.get(tc, 0.0)

            value = baselines[tc] + noise + trend + ae_shift
            value = round(max(test_item.plausible_min, min(test_item.plausible_max, value)), 1)
            visit_values[tc] = value

            records.append(VSRecord(
                canonical_id=f"{prefix}VS_{period}_{int(visitnum)}_{tc}",
                period=period, visitnum=visitnum, visit_label=visit_label,
                testcd=tc, test=test_item.test, value=value,
                unit=test_item.unit, visit_date=visit_date,
                study_day=study_day,
            ))

        # Derived record: BMI = WEIGHT(kg) / (HEIGHT(m))^2
        if 'WEIGHT' in visit_values and 'HEIGHT' in visit_values:
            height_m = visit_values['HEIGHT'] / 100.0
            if height_m > 0:
                bmi = round(visit_values['WEIGHT'] / (height_m * height_m), 1)
                bmi = max(12.0, min(60.0, bmi))  # plausible BMI range
                records.append(VSRecord(
                    canonical_id=f"{prefix}VS_{period}_{int(visitnum)}_BMI",
                    period=period, visitnum=visitnum, visit_label=visit_label,
                    testcd="BMI", test="BMI", value=bmi,
                    unit="kg/m2", visit_date=visit_date,
                    study_day=study_day,
                ))

    return records


def _generate_labs(
    rng: SubjectRNG,
    spec: TrialDesignSpec,
    treatment_sequence: List[ArmAssignment],
    first_dose_date: date,
    actual_end: date,
    latent_traits: LatentTraits,
    subj_id: str = "",
    baseline_adj: Optional['BaselineAdjustments'] = None,
    ae_events: Optional[List[AEEvent]] = None,
    sex: str = "",
    adherence: float = 1.0,
) -> List[LBRecord]:
    """Generate LB records with realistic dynamics.
    
    Realism enhancements:
    - Baseline conditioning from demographics + MH (sex-stratified Hgb, etc.)
    - AR(1) autocorrelation
    - AE → LB perturbations (e.g., Hepatotoxicity → ALT spike)
    - Normal range indicators (LBNRIND: HIGH/LOW/NORMAL)
    - Sex-stratified reference ranges
    - Visit/assessment missingness
    """
    prefix = f"{subj_id}/" if subj_id else ""
    records = []
    lb_tests = spec.lb_model.tests
    realism_cfg = spec.realism
    if baseline_adj is None:
        baseline_adj = BaselineAdjustments()
    if ae_events is None:
        ae_events = []
    
    lb_visits = _get_measurement_visits(spec, treatment_sequence, first_dose_date, actual_end, rng)
    total_visits = len(lb_visits)
    
    # Generate conditioned baseline values
    baselines = {}
    trend_mult = lab_trend_multiplier(latent_traits.baseline_severity)
    
    for test_item in lb_tests:
        adj = baseline_adj.lb_adjustments.get(test_item.testcd, 0.0)
        bl_val = rng.draw_normal("LB", "baseline", test_item.testcd,
                                 mean=test_item.baseline_mean + adj,
                                 std=test_item.baseline_sd)
        bl_val = max(test_item.plausible_min, min(test_item.plausible_max, bl_val))
        baselines[test_item.testcd] = bl_val
    
    # AR(1) state per test — test-specific rho for realistic autocorrelation
    ar_state = {t.testcd: 0.0 for t in lb_tests}
    default_rho = realism_cfg.ar1_rho_lb if realism_cfg.enable_ar1_dynamics else 0.0
    noise_scale = realism_cfg.lb_noise_scale

    # Subject-specific trend scaling: frailty modulates treatment response
    trend_scale = 0.7 + 0.6 * latent_traits.frailty_score if hasattr(latent_traits, 'frailty_score') else 1.0
    
    for v_idx, visit_info in enumerate(lb_visits):
        period = visit_info['period']
        visitnum = visit_info['visitnum']
        visit_label = visit_info['label']
        visit_date = visit_info['date']
        study_day = visit_info.get('study_day', None)
        
        if visit_date > actual_end:
            continue
        
        # Visit-level missingness (higher for labs — blood draw refusal)
        if realism_cfg.enable_missingness and total_visits > 2:
            miss_u = rng.draw("LB", "visit_miss", v_idx, RNGComponent.VISIT_ATTEND)[0]
            visit_frac = v_idx / max(total_visits - 1, 1)
            if should_miss_visit(miss_u, realism_cfg.visit_miss_rate * 1.2, visit_frac, adherence):
                continue
        
        # AE perturbations for this visit
        ae_perturbs = compute_ae_perturbations(ae_events, visit_date) if realism_cfg.enable_ae_feedback else {}
        
        for test_item in lb_tests:
            tc = test_item.testcd
            
            # Assessment-level missingness
            if realism_cfg.enable_missingness:
                assess_u = rng.draw("LB", "assess_miss", v_idx, tc, RNGComponent.ASSESS_MISS_LB)[0]
                if should_miss_assessment(assess_u, realism_cfg.lb_assessment_miss_rate):
                    records.append(LBRecord(
                        canonical_id=f"{prefix}LB_{period}_{int(visitnum)}_{tc}",
                        period=period, visitnum=visitnum, visit_label=visit_label,
                        testcd=tc, test=test_item.test, value=0.0,
                        unit=test_item.unit, visit_date=visit_date,
                        study_day=study_day, is_missing=True,
                    ))
                    continue
            
            # AR(1) noise — test-specific rho
            noise_draw = rng.draw_normal("LB", period, visitnum, tc, RNGComponent.VALUE,
                                          mean=0.0, std=1.0)
            rho = get_ar1_rho(tc, default_rho) if realism_cfg.enable_ar1_dynamics else 0.0
            if realism_cfg.enable_ar1_dynamics:
                ar_state[tc] = ar1_next_state(
                    ar_state[tc], rho,
                    test_item.baseline_sd * noise_scale, noise_draw
                )
                noise = ar_state[tc]
            else:
                noise = noise_draw * test_item.baseline_sd * 0.12

            days_on_study = (visit_date - first_dose_date).days if visit_date >= first_dose_date else 0
            trend = test_item.trend_slope * trend_mult * trend_scale * days_on_study / 30.0
            
            # AE feedback perturbation
            ae_shift = ae_perturbs.get(tc, 0.0)
            
            value = baselines[tc] + noise + trend + ae_shift
            value = round(max(test_item.plausible_min, min(test_item.plausible_max, value)), 2)
            
            # Normal range indicator
            nrind = ""
            ref_lo, ref_hi = None, None
            if realism_cfg.enable_lab_normal_range:
                nrind = lab_normal_range_ind(tc, value, sex)
                ref_lo, ref_hi = lab_reference_range(tc, sex)
            
            records.append(LBRecord(
                canonical_id=f"{prefix}LB_{period}_{int(visitnum)}_{tc}",
                period=period, visitnum=visitnum, visit_label=visit_label,
                testcd=tc, test=test_item.test, value=value,
                unit=test_item.unit, visit_date=visit_date,
                study_day=study_day,
                nrind=nrind, lbornrlo=ref_lo, lbornrhi=ref_hi,
            ))
    
    return records


def _get_measurement_visits(
    spec: TrialDesignSpec,
    treatment_sequence: List[ArmAssignment],
    first_dose_date: date,
    actual_end: date,
    rng: Optional[SubjectRNG] = None,
) -> List[Dict]:
    """Build measurement visit schedule from spec visits or generate per-period.
    
    Returns list of dicts: {period, visitnum, label, date, study_day}
    Each visit is keyed so adding/removing visits doesn't change existing ones.
    
    Realism: applies visit window jitter when enabled and rng is provided.
    """
    visits = []
    realism_cfg = spec.realism
    
    if spec.visits:
        # Use scheduled visits from spec
        visitnum_counter = 1.0
        for v in spec.visits:
            nominal_date = first_dose_date + timedelta(days=v.nominal_day - 1)
            
            # Apply visit window jitter
            visit_date = nominal_date
            if (realism_cfg.enable_visit_jitter and rng is not None
                    and (v.window_lower != 0 or v.window_upper != 0)):
                # Use record_rng directly to avoid duplicate-key warning
                # (this function is called for both VS and LB — same jitter is correct)
                jitter_rng = rng.record_rng("visit_jitter", v.visitnum)
                jitter = int(jitter_rng.integers(v.window_lower, v.window_upper + 1))
                visit_date = nominal_date + timedelta(days=jitter)
            
            if visit_date > actual_end:
                visitnum_counter += 1.0
                continue
            
            # Determine which period this visit falls in
            period = 1
            for p in treatment_sequence:
                if p.start_day <= v.nominal_day <= p.end_day:
                    period = p.period
                    break
            
            # Check VS/LB collection flags
            flags = v.collection_flags
            if not (flags.vs or flags.lb):
                visitnum_counter += 1.0
                continue
            
            visits.append({
                'period': period,
                'visitnum': v.visitnum,
                'label': v.visit,
                'date': visit_date,
                'study_day': v.nominal_day,
            })
            visitnum_counter += 1.0
    
    if not visits:
        # Generate default visits per period
        for p in treatment_sequence:
            period_duration = p.end_day - p.start_day + 1
            
            # Screening/baseline visit
            visits.append({
                'period': p.period,
                'visitnum': float(p.period * 100),
                'label': f"PERIOD {p.period} BASELINE",
                'date': first_dose_date + timedelta(days=p.start_day - 1),
                'study_day': p.start_day,
            })
            
            # Intermediate visits (every 7-14 days for longer periods)
            if period_duration > 14:
                interval = 14 if period_duration > 56 else 7
                day = p.start_day + interval
                visit_idx = 1
                while day <= p.end_day:
                    vdate = first_dose_date + timedelta(days=day - 1)
                    # Apply jitter to auto-generated intermediate visits (±2 days)
                    if realism_cfg.enable_visit_jitter and rng is not None:
                        jitter_rng = rng.record_rng("visit_jitter", float(p.period * 100 + visit_idx))
                        jitter = int(jitter_rng.integers(-2, 3))  # [-2, +2] days
                        vdate = vdate + timedelta(days=jitter)
                    if vdate > actual_end:
                        break
                    visits.append({
                        'period': p.period,
                        'visitnum': float(p.period * 100 + visit_idx),
                        'label': f"PERIOD {p.period} DAY {day - p.start_day + 1}",
                        'date': vdate,
                        'study_day': day,
                    })
                    day += interval
                    visit_idx += 1
            
            # End-of-period visit
            if period_duration > 1:
                end_date = first_dose_date + timedelta(days=p.end_day - 1)
                if end_date <= actual_end:
                    visits.append({
                        'period': p.period,
                        'visitnum': float(p.period * 100 + 99),
                        'label': f"PERIOD {p.period} END",
                        'date': end_date,
                        'study_day': p.end_day,
                    })
    
    return visits

