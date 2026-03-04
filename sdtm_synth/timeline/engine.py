"""
SDTM Synthetic Data Generator - Timeline Engine

This module generates subject timeline datasets:
- SE (Subject Elements) - actual elements traversed
- SV (Subject Visits) - actual visits attended
- DS (Disposition) - subject disposition events

It ensures temporal consistency across all domains.
"""

from __future__ import annotations
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass, field
from datetime import date, timedelta
import pandas as pd

from ..spec.models import TrialDesignSpec, ElementSpec, VisitSpec
from ..backbone.subjects import SubjectRegistry, SubjectInfo
from ..utils.rng import get_rng
from ..utils.dates import (
    format_iso_date, parse_date, derive_study_day, 
    add_days, days_between
)
from ..utils.ids import SequenceTracker


@dataclass
class SubjectTimeline:
    """Timeline information for a single subject."""
    usubjid: str
    consent_date: date
    first_dose_date: Optional[date]
    last_dose_date: Optional[date]
    end_date: Optional[date]
    element_intervals: List[Dict[str, Any]] = field(default_factory=list)
    visit_dates: Dict[int, date] = field(default_factory=dict)
    censor_date: Optional[date] = None
    
    def get_epoch_for_date(self, dt: date) -> Optional[str]:
        """
        Get the epoch for a given date.
        
        Uses half-open interval semantics [SESTDTC, SEENDTC) for all but the 
        last element to avoid ambiguity at boundaries (e.g., RFSTDTC which is
        both end of Screening and start of Treatment).
        
        This ensures dates on RFSTDTC are correctly assigned to TREATMENT,
        not SCREENING.
        """
        if not self.element_intervals:
            return None
        
        n_intervals = len(self.element_intervals)
        
        for i, interval in enumerate(self.element_intervals):
            start = interval.get('start_date')
            end = interval.get('end_date')
            
            if start is None or end is None:
                continue
            
            is_last = (i == n_intervals - 1)
            
            if is_last:
                # Last element: inclusive on both ends [start, end]
                if start <= dt <= end:
                    return interval.get('epoch')
            else:
                # Non-last elements: half-open [start, end)
                if start <= dt < end:
                    return interval.get('epoch')
        
        return None


class TimelineEngine:
    """
    Engine for generating subject timeline datasets.
    
    Generates SE, SV, and DS while ensuring:
    - SE is gapless (SEENDTC of element i equals SESTDTC of element i+1)
    - SV reflects actual visits based on participation and censoring
    - DS records disposition events at correct time points
    """
    
    def __init__(self, spec: TrialDesignSpec, registry: SubjectRegistry):
        """
        Initialize the engine.
        
        Args:
            spec: Trial design specification
            registry: Subject registry with DM data
        """
        self.spec = spec
        self.registry = registry
        self.rng = get_rng()
        self.seq_tracker = SequenceTracker()
        self.subject_timelines: Dict[str, SubjectTimeline] = {}
    
    def generate_all(self) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
        """
        Generate SE, SV, and DS datasets.
        
        Returns:
            Tuple of (SE DataFrame, SV DataFrame, DS DataFrame)
        """
        # Build timelines first
        self._build_all_timelines()
        
        # Generate datasets
        se_df = self._generate_se()
        sv_df = self._generate_sv()
        ds_df = self._generate_ds()
        
        return se_df, sv_df, ds_df
    
    def _build_all_timelines(self) -> None:
        """Build timelines for all subjects."""
        for subject in self.registry.get_all_subjects():
            timeline = self._build_subject_timeline(subject)
            self.subject_timelines[subject.usubjid] = timeline
    
    def _build_subject_timeline(self, subject: SubjectInfo) -> SubjectTimeline:
        """Build timeline for a single subject."""
        # Parse dates
        consent_date = parse_date(subject.rficdtc) if subject.rficdtc else None
        first_dose_date = parse_date(subject.rfstdtc) if subject.rfstdtc else None
        last_dose_date = parse_date(subject.rfxendtc) if subject.rfxendtc else None
        end_date = parse_date(subject.rfendtc) if subject.rfendtc else None
        
        timeline = SubjectTimeline(
            usubjid=subject.usubjid,
            consent_date=consent_date,
            first_dose_date=first_dose_date,
            last_dose_date=last_dose_date,
            end_date=end_date,
            censor_date=end_date
        )
        
        if subject.screen_failure:
            # Screen failures only have screening element
            if consent_date:
                screen_end = end_date or add_days(consent_date, self.rng.randint(7, 28))
                timeline.element_intervals.append({
                    'etcd': 'SCRN',
                    'element': 'Screening',
                    'epoch': 'SCREENING',
                    'start_date': consent_date,
                    'end_date': screen_end,
                    'taetord': 1
                })
        else:
            # Build element intervals based on arm path
            arm = self.spec.get_arm_by_code(subject.armcd)
            if arm and first_dose_date:
                current_date = consent_date
                
                # Get element sequence for this arm
                element_sequence = self.spec.get_element_sequence_for_arm(subject.armcd)
                
                for taetord, etcd in enumerate(element_sequence, start=1):
                    elem = self.spec.get_element_by_code(etcd)
                    if elem is None:
                        continue
                    
                    # Determine element duration
                    if elem.epoch.upper() == 'SCREENING':
                        # Screening ends at first dose
                        elem_start = consent_date
                        elem_end = first_dose_date
                    elif elem.epoch.upper().startswith('TREATMENT'):
                        elem_start = current_date if taetord > 1 else first_dose_date
                        duration = elem.nominal_duration_days or 56
                        elem_end = add_days(elem_start, duration)
                        
                        # Treatment elements are capped by last_dose_date, not end_date
                        if last_dose_date and elem_end > last_dose_date:
                            elem_end = last_dose_date
                        # Also cap by end_date if earlier (safety)
                        if end_date and elem_end > end_date:
                            elem_end = end_date
                        
                        # Skip if treatment has already ended
                        if last_dose_date and elem_start > last_dose_date:
                            continue
                    else:  # Follow-up or other
                        # Follow-up starts after treatment end (last_dose_date)
                        if last_dose_date and last_dose_date > current_date:
                            elem_start = last_dose_date
                        else:
                            elem_start = current_date
                        
                        duration = elem.nominal_duration_days or 28
                        elem_end = add_days(elem_start, duration)
                        
                        if end_date and elem_end > end_date:
                            elem_end = end_date
                        
                        # Skip if follow-up hasn't started or already past end
                        if end_date and elem_start >= end_date:
                            continue
                    
                    timeline.element_intervals.append({
                        'etcd': elem.etcd,
                        'element': elem.element,
                        'epoch': elem.epoch,
                        'start_date': elem_start,
                        'end_date': elem_end,
                        'taetord': taetord
                    })
                    
                    current_date = elem_end
                    
                    # Stop if we've reached censor date
                    if end_date and current_date >= end_date:
                        break
        
        # Build visit dates
        if first_dose_date:
            for visit in self.spec.visits:
                # Calculate nominal date offset from RFSTDTC
                # SDTM convention: Day 1 = RFSTDTC (offset 0), no Day 0
                # For positive days: offset = nominal_day - 1
                # For negative days: offset = nominal_day (Day -1 = 1 day before RFSTDTC)
                if visit.nominal_day >= 1:
                    day_offset = visit.nominal_day - 1
                else:
                    day_offset = visit.nominal_day
                
                nominal_date = add_days(first_dose_date, day_offset)
                
                # Window semantics:
                # window_lower/upper define the allowed deviation from nominal_day
                # For screening visits with negative nominal_day, the window typically
                # allows visits earlier (more negative) or later (toward RFSTDTC)
                # 
                # Example: nominal_day=-20, window_lower=-20, window_upper=0
                # -> actual_day can be [-40, -20] relative to RFSTDTC
                # 
                # Example: nominal_day=7, window_lower=-2, window_upper=2  
                # -> actual_day can be [5, 9] relative to RFSTDTC
                
                low = visit.window_lower if visit.window_lower else 0
                high = visit.window_upper if visit.window_upper else 0
                
                # Ensure low <= high for random generation
                if low > high:
                    low, high = high, low
                
                if low < high:
                    window = self.rng.randint(low, high)
                else:
                    # Fixed window: use the value (not 0)
                    window = low
                
                actual_date = add_days(nominal_date, window)
                
                # For screening visits (negative nominal_day), ensure date is strictly 
                # before RFSTDTC (Day 1). Cap to RFSTDTC - 1 to avoid SCREENING visit
                # landing on TREATMENT day (which causes VISIT/EPOCH mismatch).
                if visit.nominal_day < 1:
                    day_before_rfstdtc = add_days(first_dose_date, -1)
                    if actual_date >= first_dose_date:
                        actual_date = day_before_rfstdtc
                
                # Only include visits before censor date
                if end_date is None or actual_date <= end_date:
                    timeline.visit_dates[visit.visitnum] = actual_date
        
        return timeline
    
    def _generate_se(self) -> pd.DataFrame:
        """Generate Subject Elements (SE) dataset."""
        records = []
        
        for subject in self.registry.get_all_subjects():
            timeline = self.subject_timelines.get(subject.usubjid)
            if timeline is None:
                continue
            
            rfstdtc = parse_date(subject.rfstdtc) if subject.rfstdtc else None
            
            for seseq, interval in enumerate(timeline.element_intervals, start=1):
                start_date = interval['start_date']
                end_date = interval['end_date']
                
                record = {
                    'STUDYID': self.spec.study_id,
                    'DOMAIN': 'SE',
                    'USUBJID': subject.usubjid,
                    'SESEQ': seseq,
                    'ETCD': interval['etcd'],
                    'ELEMENT': interval['element'],
                    'SESTDTC': format_iso_date(start_date) if start_date else '',
                    'SEENDTC': format_iso_date(end_date) if end_date else '',
                    'EPOCH': interval['epoch'],
                    'TAETORD': interval['taetord'],
                }
                
                # Derive study days
                if rfstdtc and start_date:
                    record['SESTDY'] = derive_study_day(start_date, rfstdtc)
                else:
                    record['SESTDY'] = ''
                
                if rfstdtc and end_date:
                    record['SEENDY'] = derive_study_day(end_date, rfstdtc)
                else:
                    record['SEENDY'] = ''
                
                records.append(record)
        
        df = pd.DataFrame(records)
        
        if df.empty:
            return pd.DataFrame(columns=[
                'STUDYID', 'DOMAIN', 'USUBJID', 'SESEQ', 'ETCD', 'ELEMENT',
                'SESTDTC', 'SEENDTC', 'SESTDY', 'SEENDY', 'EPOCH', 'TAETORD'
            ])
        
        # Sort by USUBJID, SESEQ
        df = df.sort_values(['USUBJID', 'SESEQ']).reset_index(drop=True)
        
        cols = ['STUDYID', 'DOMAIN', 'USUBJID', 'SESEQ', 'ETCD', 'ELEMENT',
                'SESTDTC', 'SEENDTC', 'SESTDY', 'SEENDY', 'EPOCH', 'TAETORD']
        
        return df[[c for c in cols if c in df.columns]]
    
    def _generate_sv(self) -> pd.DataFrame:
        """Generate Subject Visits (SV) dataset."""
        records = []
        
        for subject in self.registry.get_enrolled_subjects():
            timeline = self.subject_timelines.get(subject.usubjid)
            if timeline is None:
                continue
            
            rfstdtc = parse_date(subject.rfstdtc) if subject.rfstdtc else None
            
            for visit in self.spec.visits:
                visit_date = timeline.visit_dates.get(visit.visitnum)
                
                # Determine if visit occurred
                if visit_date is not None:
                    svoccur = 'Y'
                    svstdtc = format_iso_date(visit_date)
                    svendtc = svstdtc  # Single-day visits
                    
                    # Derive study days
                    svstdy = derive_study_day(visit_date, rfstdtc) if rfstdtc else ''
                    svendy = svstdy
                    
                    # Get epoch from timeline
                    epoch = timeline.get_epoch_for_date(visit_date) or visit.epoch
                else:
                    svoccur = 'N'
                    svstdtc = ''
                    svendtc = ''
                    svstdy = ''
                    svendy = ''
                    epoch = visit.epoch
                
                record = {
                    'STUDYID': self.spec.study_id,
                    'DOMAIN': 'SV',
                    'USUBJID': subject.usubjid,
                    'VISITNUM': visit.visitnum,
                    'VISIT': visit.visit,
                    'VISITDY': visit.nominal_day,
                    'SVSTDTC': svstdtc,
                    'SVENDTC': svendtc,
                    'SVSTDY': svstdy,
                    'SVENDY': svendy,
                    'SVOCCUR': svoccur,
                    'EPOCH': epoch,
                }
                
                records.append(record)
        
        df = pd.DataFrame(records)
        
        if df.empty:
            return pd.DataFrame(columns=[
                'STUDYID', 'DOMAIN', 'USUBJID', 'VISITNUM', 'VISIT', 'VISITDY',
                'SVSTDTC', 'SVENDTC', 'SVSTDY', 'SVENDY', 'SVOCCUR', 'EPOCH'
            ])
        
        # Sort by USUBJID, VISITNUM
        df = df.sort_values(['USUBJID', 'VISITNUM']).reset_index(drop=True)
        
        cols = ['STUDYID', 'DOMAIN', 'USUBJID', 'VISITNUM', 'VISIT', 'VISITDY',
                'SVSTDTC', 'SVENDTC', 'SVSTDY', 'SVENDY', 'SVOCCUR', 'EPOCH']
        
        return df[[c for c in cols if c in df.columns]]
    
    def _generate_ds(self) -> pd.DataFrame:
        """Generate Disposition (DS) dataset."""
        records = []
        
        for subject in self.registry.get_all_subjects():
            timeline = self.subject_timelines.get(subject.usubjid)
            rfstdtc = parse_date(subject.rfstdtc) if subject.rfstdtc else None
            
            dsseq = 1
            
            # Informed consent milestone
            if subject.rficdtc:
                consent_date = parse_date(subject.rficdtc)
                # Derive epoch from timeline if available
                consent_epoch = 'SCREENING'  # Always SCREENING for consent
                record = {
                    'STUDYID': self.spec.study_id,
                    'DOMAIN': 'DS',
                    'USUBJID': subject.usubjid,
                    'DSSEQ': dsseq,
                    'DSTERM': 'INFORMED CONSENT OBTAINED',
                    'DSDECOD': 'INFORMED CONSENT OBTAINED',
                    'DSCAT': 'PROTOCOL MILESTONE',
                    'DSSCAT': '',
                    'EPOCH': consent_epoch,
                    'DSSTDTC': subject.rficdtc,
                    'DSDTC': subject.rficdtc,
                }
                if rfstdtc and consent_date:
                    record['DSDY'] = derive_study_day(consent_date, rfstdtc)
                else:
                    record['DSDY'] = ''
                records.append(record)
                dsseq += 1
            
            # Randomization (for non-screen-failures)
            if not subject.screen_failure and subject.rfstdtc:
                first_dose = parse_date(subject.rfstdtc)
                # Randomization occurs on RFSTDTC which is Day 1 (TREATMENT epoch)
                # Use timeline to derive epoch
                rand_epoch = timeline.get_epoch_for_date(first_dose) if timeline else 'TREATMENT'
                if rand_epoch is None:
                    rand_epoch = 'TREATMENT'
                record = {
                    'STUDYID': self.spec.study_id,
                    'DOMAIN': 'DS',
                    'USUBJID': subject.usubjid,
                    'DSSEQ': dsseq,
                    'DSTERM': 'RANDOMIZED',
                    'DSDECOD': 'RANDOMIZED',
                    'DSCAT': 'PROTOCOL MILESTONE',
                    'DSSCAT': '',
                    'EPOCH': rand_epoch,
                    'DSSTDTC': subject.rfstdtc,
                    'DSDTC': subject.rfstdtc,
                    'DSDY': 1,
                }
                records.append(record)
                dsseq += 1
            
            # Disposition event
            if subject.screen_failure:
                disp_term = 'SCREEN FAILURE'
                disp_date = parse_date(subject.rfpendtc) if subject.rfpendtc else None
                disp_epoch = 'SCREENING'
            elif subject.completed:
                disp_term = 'COMPLETED'
                disp_date = parse_date(subject.rfendtc) if subject.rfendtc else None
                # Derive epoch from timeline using the actual disposition date
                disp_epoch = timeline.get_epoch_for_date(disp_date) if timeline and disp_date else None
                if disp_epoch is None:
                    # Fallback: use last element's epoch
                    disp_epoch = timeline.element_intervals[-1]['epoch'] if timeline and timeline.element_intervals else 'FOLLOW-UP'
            else:
                disp_term = subject.dropout_reason or 'WITHDRAWAL BY SUBJECT'
                disp_date = parse_date(subject.rfendtc) if subject.rfendtc else None
                # Derive epoch from timeline using the actual disposition date
                disp_epoch = timeline.get_epoch_for_date(disp_date) if timeline and disp_date else None
                if disp_epoch is None:
                    disp_epoch = subject.dropout_epoch or 'TREATMENT'
            
            disp_record = {
                'STUDYID': self.spec.study_id,
                'DOMAIN': 'DS',
                'USUBJID': subject.usubjid,
                'DSSEQ': dsseq,
                'DSTERM': disp_term,
                'DSDECOD': disp_term,
                'DSCAT': 'DISPOSITION EVENT',
                'DSSCAT': 'STUDY PARTICIPATION',
                'EPOCH': disp_epoch,
                'DSSTDTC': format_iso_date(disp_date) if disp_date else '',
                'DSDTC': format_iso_date(disp_date) if disp_date else '',
            }
            
            if rfstdtc and disp_date:
                disp_record['DSDY'] = derive_study_day(disp_date, rfstdtc)
            else:
                disp_record['DSDY'] = ''
            
            records.append(disp_record)
        
        df = pd.DataFrame(records)
        
        if df.empty:
            return pd.DataFrame(columns=[
                'STUDYID', 'DOMAIN', 'USUBJID', 'DSSEQ', 'DSTERM', 'DSDECOD',
                'DSCAT', 'DSSCAT', 'EPOCH', 'DSSTDTC', 'DSDTC', 'DSDY'
            ])
        
        # Sort by USUBJID, DSSEQ
        df = df.sort_values(['USUBJID', 'DSSEQ']).reset_index(drop=True)
        
        cols = ['STUDYID', 'DOMAIN', 'USUBJID', 'DSSEQ', 'DSTERM', 'DSDECOD',
                'DSCAT', 'DSSCAT', 'EPOCH', 'DSSTDTC', 'DSDTC', 'DSDY']
        
        return df[[c for c in cols if c in df.columns]]
    
    def get_subject_timeline(self, usubjid: str) -> Optional[SubjectTimeline]:
        """Get timeline for a specific subject."""
        return self.subject_timelines.get(usubjid)
    
    def get_censor_date(self, usubjid: str) -> Optional[date]:
        """Get censor date for a subject."""
        timeline = self.subject_timelines.get(usubjid)
        return timeline.censor_date if timeline else None
