"""
SDTM Materializer — §2.1 / Contract 10

Renders CanonicalSubject objects into SDTM-compliant DataFrames.
SDTM is a projected view of canonical truth.
"""

from __future__ import annotations
import csv
from datetime import date, timedelta
from typing import List, Dict, Optional, Tuple
import pandas as pd

from .canonical import CanonicalSubject, AEEvent, ArmAssignment, VSRecord, LBRecord
from .provenance import ProvenanceMap, CanonicalRelationship
from ..utils.dates import format_iso_date, derive_study_day


def _accumulate_batch(
    subjects: List[CanonicalSubject],
    spec,
    dm_records: list, ae_records: list, ds_records: list,
    ex_records: list, cm_records: list, mh_records: list,
    sv_records: list, se_records: list, vs_records: list, lb_records: list,
    provenance: ProvenanceMap,
    relationships: list,
) -> None:
    """
    Materialize one batch of subjects into shared accumulator lists.

    All list/provenance/relationship arguments are mutated in-place.
    Subjects must be pre-sorted by subject_index.
    """
    study_id = spec.study_id

    for subj in subjects:
        usubjid = f"{study_id}-{subj.identity.siteid}-{subj.identity.subjid}"
        first_dose = _get_first_dose_date(subj)
        rfstdtc = first_dose
        subj_prefix = f"{subj.identity.canonical_id}/"

        # ── DM ──
        dm_records.append(_materialize_dm(subj, study_id, usubjid, first_dose))

        if subj.is_screen_failure:
            ds_consent = _make_ds_record(study_id, usubjid, 1, "INFORMED CONSENT OBTAINED",
                                          "INFORMED CONSENT OBTAINED", "PROTOCOL MILESTONE", "",
                                          subj.timeline.consent_date, rfstdtc)
            ds_records.append(ds_consent)
            provenance.register(f"{subj_prefix}DS_PROTOCOL_MILESTONE_CONSENT", "DS", usubjid, 1)

            ds_sf = _make_ds_record(study_id, usubjid, 2, "SCREEN FAILURE", "SCREEN FAILURE",
                                     "PROTOCOL MILESTONE", "", subj.disposition.date, rfstdtc)
            ds_records.append(ds_sf)
            provenance.register(f"{subj_prefix}DS_PROTOCOL_MILESTONE_SCREENFAIL", "DS", usubjid, 2)
            continue

        # ── AE ──
        sorted_aes = sorted(subj.adverse_events, key=lambda a: (a.onset_date, a.canonical_id))
        for seq, ae in enumerate(sorted_aes, 1):
            ae_rec = _materialize_ae(ae, study_id, usubjid, seq, rfstdtc, subj)
            ae_records.append(ae_rec)
            provenance.register(ae.canonical_id, "AE", usubjid, seq)

        # ── DS ──
        ds_seq = 1
        ds_rec = _make_ds_record(study_id, usubjid, ds_seq, "INFORMED CONSENT OBTAINED",
                                  "INFORMED CONSENT OBTAINED", "PROTOCOL MILESTONE", "",
                                  subj.timeline.consent_date, rfstdtc)
        ds_records.append(ds_rec)
        provenance.register(f"{subj_prefix}DS_PROTOCOL_MILESTONE_CONSENT", "DS", usubjid, ds_seq)
        ds_seq += 1

        ds_rec = _make_ds_record(study_id, usubjid, ds_seq, "RANDOMIZED", "RANDOMIZED",
                                  "PROTOCOL MILESTONE", "", first_dose, rfstdtc)
        ds_records.append(ds_rec)
        provenance.register(f"{subj_prefix}DS_PROTOCOL_MILESTONE_RANDOMIZED", "DS", usubjid, ds_seq)
        ds_seq += 1

        if subj.disposition.outcome == "COMPLETED":
            ds_rec = _make_ds_record(study_id, usubjid, ds_seq, "COMPLETED", "COMPLETED",
                                      "DISPOSITION EVENT", "", subj.disposition.date, rfstdtc)
            ds_records.append(ds_rec)
            provenance.register(f"{subj_prefix}DS_DISPOSITION_COMPLETED", "DS", usubjid, ds_seq)
        elif subj.disposition.outcome == "DEATH":
            ds_rec = _make_ds_record(study_id, usubjid, ds_seq, "DEATH", "DEATH",
                                      "DISPOSITION EVENT", "", subj.death.date if subj.death else subj.disposition.date, rfstdtc)
            ds_records.append(ds_rec)
            death_ds_canonical = f"{subj_prefix}DS_OTHER_DEATH"
            provenance.register(death_ds_canonical, "DS", usubjid, ds_seq)

            if subj.death and subj.death.linked_ae_id:
                rel = CanonicalRelationship(
                    rel_id=f"{subj.death.linked_ae_id}|{death_ds_canonical}|AE_FATAL_TO_DS|0",
                    source_id=subj.death.linked_ae_id,
                    target_id=death_ds_canonical,
                    relationship_type="AE_FATAL_TO_DS",
                    usubjid=usubjid,
                )
                relationships.append(rel)
        else:
            ds_rec = _make_ds_record(study_id, usubjid, ds_seq,
                                      subj.disposition.reason, subj.disposition.reason,
                                      "DISPOSITION EVENT", "", subj.disposition.date, rfstdtc)
            ds_records.append(ds_rec)
            disp_canonical = f"{subj_prefix}DS_DISPOSITION_{subj.disposition.reason.replace(' ', '_').upper()}"
            provenance.register(disp_canonical, "DS", usubjid, ds_seq)

            if subj.disposition.linked_ae_id and subj.disposition.outcome == "ADVERSE EVENT":
                rel = CanonicalRelationship(
                    rel_id=f"{subj.disposition.linked_ae_id}|{disp_canonical}|AE_CAUSES_DS|0",
                    source_id=subj.disposition.linked_ae_id,
                    target_id=disp_canonical,
                    relationship_type="AE_CAUSES_DS",
                    usubjid=usubjid,
                )
                relationships.append(rel)
        ds_seq += 1

        # ── EX ──
        sorted_ex = sorted(subj.exposures, key=lambda e: (e.period, e.start_date or date.min))
        for seq, ex in enumerate(sorted_ex, 1):
            ex_records.append(_materialize_ex(ex, study_id, usubjid, seq, rfstdtc, subj))
            provenance.register(ex.canonical_id, "EX", usubjid, seq)

        # ── CM ──
        sorted_cm = sorted(subj.conmeds, key=lambda c: (c.start_date or date.min, c.canonical_id))
        for seq, cm in enumerate(sorted_cm, 1):
            cm_records.append(_materialize_cm(cm, study_id, usubjid, seq, rfstdtc))
            provenance.register(cm.canonical_id, "CM", usubjid, seq)

            if cm.linked_ae_id:
                rel = CanonicalRelationship(
                    rel_id=f"{cm.linked_ae_id}|{cm.canonical_id}|AE_TREATED_BY_CM|0",
                    source_id=cm.linked_ae_id,
                    target_id=cm.canonical_id,
                    relationship_type="AE_TREATED_BY_CM",
                    usubjid=usubjid,
                )
                relationships.append(rel)

        # ── MH ──
        sorted_mh = sorted(subj.medical_history, key=lambda m: m.term)
        for seq, mh in enumerate(sorted_mh, 1):
            mh_records.append(_materialize_mh(mh, study_id, usubjid, seq, rfstdtc))
            provenance.register(mh.canonical_id, "MH", usubjid, seq)

        # ── SE ──
        for seq, span in enumerate(subj.timeline.element_spans, 1):
            se_records.append(_materialize_se(span, study_id, usubjid, seq, first_dose, rfstdtc))

        # ── SV ──
        sv_recs = _materialize_sv(subj, spec, study_id, usubjid, first_dose, rfstdtc)
        sv_records.extend(sv_recs)

        # ── VS ──
        sorted_vs = sorted(subj.vs_records, key=lambda r: (r.period, r.visitnum, r.testcd))
        for seq, vs in enumerate(sorted_vs, 1):
            vs_records.append(_materialize_vs(vs, study_id, usubjid, seq, rfstdtc, subj))
            provenance.register(vs.canonical_id, "VS", usubjid, seq)

        # ── LB ──
        sorted_lb = sorted(subj.lb_records, key=lambda r: (r.period, r.visitnum, r.testcd))
        for seq, lb in enumerate(sorted_lb, 1):
            lb_records.append(_materialize_lb(lb, study_id, usubjid, seq, rfstdtc, subj))
            provenance.register(lb.canonical_id, "LB", usubjid, seq)


def materialize_batched(
    subjects_iter,
    spec,
    batch_size: int = 500,
    provenance: Optional[ProvenanceMap] = None,
) -> Tuple[Dict[str, pd.DataFrame], ProvenanceMap, List[CanonicalRelationship]]:
    """
    Materialize SDTM domains from an iterable of canonical subjects in batches.

    Processes subjects in chunks of batch_size, releasing each batch's
    CanonicalSubject objects after materializing into flat record dicts.
    Peak memory for subject objects is O(batch_size) instead of O(N).

    Output is identical to materialize_all() — the same _to_df() domain-wide
    sort ensures deterministic row ordering regardless of batch boundaries.

    Args:
        subjects_iter: Any iterable of CanonicalSubject (list, generator, etc.)
        spec: TrialDesignSpec
        batch_size: Subjects per batch (default 500)
        provenance: Optional shared ProvenanceMap (created if None)

    Returns:
        (datasets dict, provenance map, relationships list)
    """
    if provenance is None:
        provenance = ProvenanceMap()

    relationships: List[CanonicalRelationship] = []

    # Shared accumulator lists — persist across batches
    dm_records, ae_records, ds_records = [], [], []
    ex_records, cm_records, mh_records = [], [], []
    sv_records, se_records = [], []
    vs_records, lb_records = [], []

    # Consume iterable in batches
    batch: List[CanonicalSubject] = []
    for subj in subjects_iter:
        batch.append(subj)
        if len(batch) >= batch_size:
            batch.sort(key=lambda s: s.identity.subject_index)
            _accumulate_batch(
                batch, spec,
                dm_records, ae_records, ds_records,
                ex_records, cm_records, mh_records,
                sv_records, se_records, vs_records, lb_records,
                provenance, relationships,
            )
            batch.clear()

    # Flush final partial batch
    if batch:
        batch.sort(key=lambda s: s.identity.subject_index)
        _accumulate_batch(
            batch, spec,
            dm_records, ae_records, ds_records,
            ex_records, cm_records, mh_records,
            sv_records, se_records, vs_records, lb_records,
            provenance, relationships,
        )

    # Build DataFrames (domain-wide sort via _to_df)
    datasets = {}
    datasets['DM'] = _to_df(dm_records, 'DM')
    datasets['AE'] = _to_df(ae_records, 'AE')
    datasets['DS'] = _to_df(ds_records, 'DS')
    datasets['EX'] = _to_df(ex_records, 'EX')
    datasets['CM'] = _to_df(cm_records, 'CM')
    datasets['MH'] = _to_df(mh_records, 'MH')
    datasets['SE'] = _to_df(se_records, 'SE')
    datasets['SV'] = _to_df(sv_records, 'SV')
    datasets['VS'] = _to_df(vs_records, 'VS')
    datasets['LB'] = _to_df(lb_records, 'LB')

    # Build RELREC from complete provenance
    datasets['RELREC'] = provenance.rebuild_relrec(relationships, study_id=spec.study_id)

    return datasets, provenance, relationships


def materialize_all(
    subjects: List[CanonicalSubject],
    spec,
    provenance: Optional[ProvenanceMap] = None,
) -> Tuple[Dict[str, pd.DataFrame], ProvenanceMap, List[CanonicalRelationship]]:
    """
    Materialize all SDTM domains from canonical subjects.

    Backward-compatible wrapper around materialize_batched.
    Processes all subjects in a single batch.

    Returns:
        (datasets dict, provenance map, relationships list)
    """
    return materialize_batched(
        iter(subjects), spec,
        batch_size=len(subjects) + 1,
        provenance=provenance,
    )


def _to_df(records: list, domain: str) -> pd.DataFrame:
    """Convert records list to DataFrame with deterministic sort."""
    from ..schema.column_order import DOMAIN_COLUMN_ORDER, DOMAIN_ROW_SORT_KEYS
    
    if not records:
        cols = DOMAIN_COLUMN_ORDER.get(domain, ['STUDYID', 'DOMAIN', 'USUBJID'])
        return pd.DataFrame(columns=cols)
    
    df = pd.DataFrame(records)
    
    # Apply column order
    col_order = DOMAIN_COLUMN_ORDER.get(domain)
    if col_order:
        available = [c for c in col_order if c in df.columns]
        extra = [c for c in df.columns if c not in col_order]
        df = df[available + extra]
    
    # Apply sort
    sort_keys = DOMAIN_ROW_SORT_KEYS.get(domain)
    if sort_keys:
        valid_keys = [k for k in sort_keys if k in df.columns]
        if valid_keys:
            df = df.sort_values(valid_keys).reset_index(drop=True)
    
    return df


def _get_first_dose_date(subj: CanonicalSubject) -> Optional[date]:
    """Get first dose date from canonical timeline (v2: stable from generator)."""
    if subj.is_screen_failure:
        return None
    # v2: use the stored first_dose_date from the generation pipeline
    if subj.timeline.first_dose_date:
        return subj.timeline.first_dose_date
    # Fallback: derive from exposures or timeline
    if subj.exposures:
        dates = [e.start_date for e in subj.exposures if e.start_date]
        return min(dates) if dates else subj.timeline.consent_date + timedelta(days=14)
    if subj.treatment_sequence:
        return subj.timeline.consent_date + timedelta(days=subj.treatment_sequence[0].start_day + 13)
    return subj.timeline.consent_date + timedelta(days=14)


def _materialize_dm(subj: CanonicalSubject, study_id: str, usubjid: str, first_dose: Optional[date]) -> dict:
    """Render DM row from canonical subject."""
    is_sf = subj.is_screen_failure
    
    rec = {
        'STUDYID': study_id,
        'DOMAIN': 'DM',
        'USUBJID': usubjid,
        'SUBJID': subj.identity.subjid,
        'SITEID': subj.identity.siteid,
        'BRTHDTC': str(subj.timeline.consent_date.year - subj.demographics.age) if subj.demographics.age else '',
        'AGE': subj.demographics.age,
        'AGEU': 'YEARS',
        'SEX': subj.demographics.sex,
        'RACE': subj.demographics.race,
        'ETHNIC': subj.demographics.ethnic,
        'ARMCD': '' if is_sf else subj.arm_code,
        'ARM': '' if is_sf else subj.arm_label,
        'ACTARMCD': '' if is_sf else subj.arm_code,
        'ACTARM': '' if is_sf else subj.arm_label,
        'ARMNRS': 'SCREEN FAILURE' if is_sf else '',
        'COUNTRY': subj.identity.country,
        'INVNAM': '',
        'RFSTDTC': '' if is_sf else (format_iso_date(first_dose) if first_dose else ''),
        'RFENDTC': '' if is_sf else (format_iso_date(subj.end_date) if subj.end_date else ''),
        'RFXSTDTC': '' if is_sf else (format_iso_date(first_dose) if first_dose else ''),
        'RFXENDTC': '',
        'RFICDTC': format_iso_date(subj.timeline.consent_date),
        'RFPENDTC': '' if is_sf else (format_iso_date(subj.end_date) if subj.end_date else ''),
        'DTHDTC': format_iso_date(subj.death.date) if subj.death else '',
        'DTHFL': 'Y' if subj.death else '',
    }
    
    # RFXENDTC = last exposure end
    if not is_sf and subj.exposures:
        last_ex = max((e for e in subj.exposures if e.end_date), key=lambda e: e.end_date, default=None)
        if last_ex:
            rec['RFXENDTC'] = format_iso_date(last_ex.end_date)
    
    return rec


def _materialize_ae(ae: AEEvent, study_id: str, usubjid: str, seq: int, rfstdtc: Optional[date], subj: CanonicalSubject) -> dict:
    """Render AE row with full MedDRA hierarchy (Phase 2)."""
    end_date = ae.onset_date + timedelta(days=ae.duration_days) if ae.duration_days > 0 else None
    if ae.is_fatal and subj.death:
        end_date = subj.death.date
    
    # Determine epoch from element spans
    epoch = _get_epoch_for_date(ae.onset_date, subj, rfstdtc)
    
    rec = {
        'STUDYID': study_id,
        'DOMAIN': 'AE',
        'USUBJID': usubjid,
        'AESEQ': seq,
        'AELNKID': f"AE{seq}",
        'AETERM': ae.term,
        'AEDECOD': ae.decoded_term,
        'AEPTCD': ae.pt_code if ae.pt_code else '',
        'AEHLT': ae.hlt_name if ae.hlt_name else '',
        'AEHLTCD': ae.hlt_code if ae.hlt_code else '',
        'AEHLGT': ae.hlgt_name if ae.hlgt_name else '',
        'AEHLGTCD': ae.hlgt_code if ae.hlgt_code else '',
        'AEBODSYS': ae.body_system,
        'AEBDSYCD': ae.soc_code if ae.soc_code else '',
        'AESOC': ae.soc_name if ae.soc_name else ae.body_system,
        'AESOCCD': ae.soc_code if ae.soc_code else '',
        'AESEV': ae.severity,
        'AESER': 'Y' if ae.is_serious else 'N',
        'AESDTH': 'Y' if ae.is_fatal else 'N',
        'AEREL': ae.relationship,
        'AEOUT': ae.outcome,
        'AEACN': ae.action if not ae.is_fatal else 'NOT APPLICABLE',
        'AESTDTC': format_iso_date(ae.onset_date),
        'AEENDTC': format_iso_date(end_date) if end_date else '',
        'AESTDY': derive_study_day(ae.onset_date, rfstdtc) if rfstdtc else '',
        'AEENDY': derive_study_day(end_date, rfstdtc) if (end_date and rfstdtc) else '',
        'EPOCH': epoch,
    }
    return rec


def _make_ds_record(study_id, usubjid, seq, term, decod, cat, scat, dt, rfstdtc) -> dict:
    return {
        'STUDYID': study_id,
        'DOMAIN': 'DS',
        'USUBJID': usubjid,
        'DSSEQ': seq,
        'DSTERM': term,
        'DSDECOD': decod,
        'DSCAT': cat,
        'DSSCAT': scat,
        'DSLNKID': '',
        'DSSTDTC': format_iso_date(dt) if dt else '',
        'DSSTDY': derive_study_day(dt, rfstdtc) if (dt and rfstdtc) else '',
        'EPOCH': '',
    }


def _materialize_ex(ex, study_id, usubjid, seq, rfstdtc, subj) -> dict:
    epoch = _get_epoch_for_date(ex.start_date, subj, rfstdtc) if ex.start_date else ''
    return {
        'STUDYID': study_id,
        'DOMAIN': 'EX',
        'USUBJID': usubjid,
        'EXSEQ': seq,
        'EXTRT': ex.treatment,
        'EXDOSE': ex.dose,
        'EXDOSU': ex.dose_unit,
        'EXDOSFRM': ex.form,
        'EXDOSFRQ': ex.frequency,
        'EXROUTE': ex.route,
        'EXSTDTC': format_iso_date(ex.start_date) if ex.start_date else '',
        'EXENDTC': format_iso_date(ex.end_date) if ex.end_date else '',
        'EXSTDY': derive_study_day(ex.start_date, rfstdtc) if (ex.start_date and rfstdtc) else '',
        'EXENDY': derive_study_day(ex.end_date, rfstdtc) if (ex.end_date and rfstdtc) else '',
        'VISITNUM': '',
        'VISIT': '',
        'EPOCH': epoch,
    }


def _materialize_cm(cm, study_id, usubjid, seq, rfstdtc) -> dict:
    return {
        'STUDYID': study_id,
        'DOMAIN': 'CM',
        'USUBJID': usubjid,
        'CMSEQ': seq,
        'CMTRT': cm.treatment,
        'CMDECOD': cm.decoded,
        'CMCAT': cm.category,
        'CMDOSE': cm.dose if cm.dose else '',
        'CMDOSU': cm.dose_unit if cm.dose else '',
        'CMDOSFRQ': cm.frequency,
        'CMROUTE': cm.route,
        'CMSTDTC': format_iso_date(cm.start_date) if cm.start_date else '',
        'CMENDTC': format_iso_date(cm.end_date) if cm.end_date else '',
        'CMSTDY': derive_study_day(cm.start_date, rfstdtc) if (cm.start_date and rfstdtc) else '',
        'CMENDY': derive_study_day(cm.end_date, rfstdtc) if (cm.end_date and rfstdtc) else '',
        'CMINDC': cm.indication,
        'EPOCH': '',
    }


def _materialize_mh(mh, study_id, usubjid, seq, rfstdtc) -> dict:
    # Use partial date for MHSTDTC if available (more realistic)
    mh_start = ''
    if hasattr(mh, 'start_date_partial') and mh.start_date_partial:
        mh_start = mh.start_date_partial
    elif mh.start_date:
        mh_start = format_iso_date(mh.start_date)
    
    return {
        'STUDYID': study_id,
        'DOMAIN': 'MH',
        'USUBJID': usubjid,
        'MHSEQ': seq,
        'MHTERM': mh.term,
        'MHDECOD': mh.term,
        'MHCAT': mh.category,
        'MHSCAT': mh.subcategory,
        'MHBODSYS': '',
        'MHSTDTC': mh_start,
        'MHENDTC': format_iso_date(mh.end_date) if mh.end_date else '',
        'MHENRF': 'ONGOING' if mh.is_ongoing else '',
        'MHDY': '',
        'EPOCH': '',
    }


def _materialize_se(span, study_id, usubjid, seq, first_dose, rfstdtc) -> dict:
    start = first_dose + timedelta(days=span.start_day - 1) if first_dose else None
    end = first_dose + timedelta(days=span.end_day - 1) if first_dose else None
    return {
        'STUDYID': study_id,
        'DOMAIN': 'SE',
        'USUBJID': usubjid,
        'SESEQ': seq,
        'ETCD': span.element[:8].upper().replace(' ', ''),
        'ELEMENT': span.element,
        'SESTDTC': format_iso_date(start) if start else '',
        'SEENDTC': format_iso_date(end) if end else '',
        'SESTDY': derive_study_day(start, rfstdtc) if (start and rfstdtc) else '',
        'SEENDY': derive_study_day(end, rfstdtc) if (end and rfstdtc) else '',
        'EPOCH': span.epoch,
    }


def _materialize_sv(subj, spec, study_id, usubjid, first_dose, rfstdtc) -> list:
    """Generate SV records from spec visits with jittered dates.
    
    Uses the same jitter RNG derivation as VS/LB so visit dates are consistent.
    """
    from ..utils.rng import SubjectRNG
    
    if not first_dose or subj.is_screen_failure:
        return []
    
    records = []
    end_date = subj.end_date or first_dose + timedelta(days=200)
    realism_cfg = spec.realism
    
    # Create same RNG as subject generator to get consistent jitter
    rng = SubjectRNG(spec.study_seed, subj.identity.subject_index, spec.study_id)
    
    for seq, visit in enumerate(spec.visits, 1):
        nominal_date = first_dose + timedelta(days=visit.nominal_day - 1)
        visit_date = nominal_date
        
        # Apply same jitter as measurement visits
        if (realism_cfg.enable_visit_jitter
                and (visit.window_lower != 0 or visit.window_upper != 0)):
            jitter_rng = rng.record_rng("visit_jitter", visit.visitnum)
            jitter = int(jitter_rng.integers(visit.window_lower, visit.window_upper + 1))
            visit_date = nominal_date + timedelta(days=jitter)
        
        if visit_date > end_date and visit.nominal_day > 1:
            continue
        
        records.append({
            'STUDYID': study_id,
            'DOMAIN': 'SV',
            'USUBJID': usubjid,
            'SVSEQ': seq,
            'VISITNUM': visit.visitnum,
            'VISIT': visit.visit,
            'SVSTDTC': format_iso_date(visit_date),
            'SVENDTC': format_iso_date(visit_date),
            'SVSTDY': derive_study_day(visit_date, rfstdtc) if rfstdtc else '',
            'SVENDY': derive_study_day(visit_date, rfstdtc) if rfstdtc else '',
            'EPOCH': visit.epoch or '',
        })
    
    return records


def _get_epoch_for_date(dt: Optional[date], subj: CanonicalSubject, rfstdtc: Optional[date]) -> str:
    """Determine epoch for a date based on element spans."""
    if not dt or not rfstdtc or not subj.timeline.element_spans:
        return 'TREATMENT'
    
    study_day = (dt - rfstdtc).days + 1
    for span in subj.timeline.element_spans:
        if span.start_day <= study_day <= span.end_day:
            return span.epoch
    
    return 'TREATMENT'


def export_datasets(datasets: Dict[str, pd.DataFrame], output_dir: str):
    """Export datasets to CSV per Contract 10."""
    import os
    os.makedirs(output_dir, exist_ok=True)
    
    for domain, df in datasets.items():
        if df is None or len(df) == 0:
            continue
        
        path = os.path.join(output_dir, f"{domain.lower()}.csv")
        df.to_csv(
            path,
            index=False,
            header=True,
            lineterminator="\n",
            encoding="utf-8",
            quoting=csv.QUOTE_MINIMAL,
            na_rep="",
        )


# ─── Phase 2: VS/LB Materialization ──────────────────────────────────────────

def _materialize_vs(vs: VSRecord, study_id: str, usubjid: str, seq: int, 
                     rfstdtc, subj: CanonicalSubject) -> dict:
    """Render VS row from canonical truth."""
    epoch = _get_epoch_for_date(vs.visit_date, subj, rfstdtc)
    
    if vs.is_missing:
        return {
            'STUDYID': study_id,
            'DOMAIN': 'VS',
            'USUBJID': usubjid,
            'VSSEQ': seq,
            'VSTESTCD': vs.testcd,
            'VSTEST': vs.test,
            'VSORRES': '',
            'VSORRESU': vs.unit,
            'VSSTRESC': '',
            'VSSTRESN': '',
            'VSSTRESU': vs.unit,
            'VSSTAT': 'NOT DONE',
            'VISITNUM': vs.visitnum,
            'VISIT': vs.visit_label,
            'VSDTC': format_iso_date(vs.visit_date) if vs.visit_date else '',
            'VSDY': derive_study_day(vs.visit_date, rfstdtc) if (vs.visit_date and rfstdtc) else '',
            'EPOCH': epoch,
        }
    
    return {
        'STUDYID': study_id,
        'DOMAIN': 'VS',
        'USUBJID': usubjid,
        'VSSEQ': seq,
        'VSTESTCD': vs.testcd,
        'VSTEST': vs.test,
        'VSORRES': str(vs.value),
        'VSORRESU': vs.unit,
        'VSSTRESC': str(vs.value),
        'VSSTRESN': vs.value,
        'VSSTRESU': vs.unit,
        'VSSTAT': '',
        'VISITNUM': vs.visitnum,
        'VISIT': vs.visit_label,
        'VSDTC': format_iso_date(vs.visit_date) if vs.visit_date else '',
        'VSDY': derive_study_day(vs.visit_date, rfstdtc) if (vs.visit_date and rfstdtc) else '',
        'EPOCH': epoch,
    }


def _materialize_lb(lb: LBRecord, study_id: str, usubjid: str, seq: int,
                     rfstdtc, subj: CanonicalSubject) -> dict:
    """Render LB row from canonical truth with normal range indicators."""
    epoch = _get_epoch_for_date(lb.visit_date, subj, rfstdtc)
    
    if lb.is_missing:
        return {
            'STUDYID': study_id,
            'DOMAIN': 'LB',
            'USUBJID': usubjid,
            'LBSEQ': seq,
            'LBTESTCD': lb.testcd,
            'LBTEST': lb.test,
            'LBCAT': 'CHEMISTRY' if lb.testcd in ('ALT', 'AST', 'CREAT', 'GLUC') else 'HEMATOLOGY',
            'LBORRES': '',
            'LBORRESU': lb.unit,
            'LBSTRESC': '',
            'LBSTRESN': '',
            'LBSTRESU': lb.unit,
            'LBSTAT': 'NOT DONE',
            'LBNRIND': '',
            'LBORNRLO': '',
            'LBORNRHI': '',
            'VISITNUM': lb.visitnum,
            'VISIT': lb.visit_label,
            'LBDTC': format_iso_date(lb.visit_date) if lb.visit_date else '',
            'LBDY': derive_study_day(lb.visit_date, rfstdtc) if (lb.visit_date and rfstdtc) else '',
            'EPOCH': epoch,
        }
    
    return {
        'STUDYID': study_id,
        'DOMAIN': 'LB',
        'USUBJID': usubjid,
        'LBSEQ': seq,
        'LBTESTCD': lb.testcd,
        'LBTEST': lb.test,
        'LBCAT': 'CHEMISTRY' if lb.testcd in ('ALT', 'AST', 'CREAT', 'GLUC') else 'HEMATOLOGY',
        'LBORRES': str(lb.value),
        'LBORRESU': lb.unit,
        'LBSTRESC': str(lb.value),
        'LBSTRESN': lb.value,
        'LBSTRESU': lb.unit,
        'LBSTAT': '',
        'LBNRIND': lb.nrind,
        'LBORNRLO': lb.lbornrlo if lb.lbornrlo is not None else '',
        'LBORNRHI': lb.lbornrhi if lb.lbornrhi is not None else '',
        'VISITNUM': lb.visitnum,
        'VISIT': lb.visit_label,
        'LBDTC': format_iso_date(lb.visit_date) if lb.visit_date else '',
        'LBDY': derive_study_day(lb.visit_date, rfstdtc) if (lb.visit_date and rfstdtc) else '',
        'EPOCH': epoch,
    }
