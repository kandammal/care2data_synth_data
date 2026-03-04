"""
SDTM Synthetic Data Generator - Exposure Generator

This module generates the Exposure (EX) dataset.
"""

from __future__ import annotations
from typing import List, Dict, Any, Optional
from datetime import date, timedelta
import pandas as pd

from ..spec.models import TrialDesignSpec, RegimenItem, DoseFrequency, Route
from ..backbone.subjects import SubjectRegistry, SubjectInfo
from ..timeline.engine import TimelineEngine, SubjectTimeline
from ..utils.rng import get_rng
from ..utils.dates import format_iso_date, parse_date, derive_study_day, add_days
from ..utils.ids import SequenceTracker


class ExposureGenerator:
    """
    Generates the Exposure (EX) dataset.
    
    Tracks drug administration based on:
    - Arm-specific regimens
    - Visit schedule
    - Subject censoring dates
    
    Supports two exposure recording modes:
    - "period": One record per continuous dosing period (recommended for most trials)
    - "daily": One record per dose date (for detailed tracking)
    """
    
    def __init__(self, 
                 spec: TrialDesignSpec, 
                 registry: SubjectRegistry,
                 timeline_engine: TimelineEngine,
                 exposure_mode: str = "period"):
        """
        Initialize the generator.
        
        Args:
            spec: Trial design specification
            registry: Subject registry
            timeline_engine: Timeline engine with subject timelines
            exposure_mode: "period" for consolidated records, "daily" for per-dose records
        """
        self.spec = spec
        self.registry = registry
        self.timeline_engine = timeline_engine
        self.rng = get_rng()
        self.seq_tracker = SequenceTracker()
        self.exposure_mode = exposure_mode  # "period" or "daily"
    
    def generate(self) -> pd.DataFrame:
        """
        Generate EX dataset.
        
        Returns:
            EX DataFrame
        """
        records = []
        
        for subject in self.registry.get_enrolled_subjects():
            subject_records = self._generate_subject_ex(subject)
            records.extend(subject_records)
        
        if not records:
            return self._empty_ex()
        
        df = pd.DataFrame(records)
        
        # Sort by USUBJID, EXSEQ
        df = df.sort_values(['USUBJID', 'EXSEQ']).reset_index(drop=True)
        
        cols = ['STUDYID', 'DOMAIN', 'USUBJID', 'EXSEQ', 'EXTRT', 'EXCAT',
                'EXDOSE', 'EXDOSU', 'EXDOSFRM', 'EXROUTE', 'EXDOSFRQ',
                'EXSTDTC', 'EXENDTC', 'EXSTDY', 'EXENDY', 'EPOCH', 'VISITNUM', 'VISIT']
        
        return df[[c for c in cols if c in df.columns]]
    
    def _generate_subject_ex(self, subject: SubjectInfo) -> List[Dict[str, Any]]:
        """Generate EX records for a single subject."""
        records = []
        
        # Get arm regimen
        arm = self.spec.get_arm_by_code(subject.armcd)
        if arm is None or not arm.regimen:
            return records
        
        # Get timeline
        timeline = self.timeline_engine.get_subject_timeline(subject.usubjid)
        if timeline is None:
            return records
        
        rfstdtc = parse_date(subject.rfstdtc) if subject.rfstdtc else None
        first_dose_date = timeline.first_dose_date
        last_dose_date = timeline.last_dose_date
        
        if first_dose_date is None:
            return records
        
        # Generate exposure records for each regimen
        for regimen in arm.regimen:
            regimen_records = self._generate_regimen_records(
                subject, regimen, timeline, rfstdtc, first_dose_date, last_dose_date
            )
            records.extend(regimen_records)
        
        return records
    
    def _generate_regimen_records(
        self, 
        subject: SubjectInfo,
        regimen: RegimenItem,
        timeline: SubjectTimeline,
        rfstdtc: Optional[date],
        first_dose_date: date,
        last_dose_date: Optional[date]
    ) -> List[Dict[str, Any]]:
        """
        Generate EX records for a specific regimen.
        
        Automatically selects the appropriate mode:
        - Intermittent dosing (Q2W, Q4W, etc.) with IV/SC/IM: One record per dose
        - Daily oral dosing (QD, BID, TID): One record per treatment period
        
        Per SDTM-IG: For intermittent dosing like IV infusions, each administration
        should be represented as a separate record.
        """
        records = []
        
        # Determine dosing pattern
        frequency = regimen.frequency.value if hasattr(regimen.frequency, 'value') else str(regimen.frequency)
        freq_lower = frequency.lower()
        
        # Check if this is intermittent dosing (clinic-administered)
        # Q2W, Q4W, Q1W, QW dosing with injectable routes should be per-dose records
        is_intermittent = any(x in freq_lower for x in ['q2w', 'q4w', 'q1w', 'qw', 'weekly', 'biweekly', 'monthly'])
        is_injectable = regimen.route in (Route.INTRAVENOUS, Route.SUBCUTANEOUS, Route.INTRAMUSCULAR)
        
        # Check regimen mode override FIRST - mode="visit" takes priority
        # This ensures dosing happens at exact protocol-specified visit days
        regimen_mode = getattr(regimen, 'mode', None)
        if regimen_mode == 'visit':
            return self._generate_visit_based_dose_records(
                subject, regimen, timeline, rfstdtc, first_dose_date, last_dose_date, frequency
            )
        
        # For intermittent injectable dosing without mode="visit", generate one record per dose
        if is_intermittent and is_injectable:
            return self._generate_intermittent_dose_records(
                subject, regimen, timeline, rfstdtc, first_dose_date, last_dose_date, frequency
            )
        
        # For daily/period mode, use treatment intervals
        treatment_intervals = self._get_treatment_intervals(timeline, regimen)
        
        if not treatment_intervals:
            # Fallback: use first_dose_date to last_dose_date
            if last_dose_date and first_dose_date:
                treatment_intervals = [(first_dose_date, last_dose_date)]
            else:
                return records
        
        # Generate records for each treatment interval
        for interval_start, interval_end in treatment_intervals:
            # Cap to last_dose_date if subject dropped out early
            actual_end = interval_end
            if last_dose_date and last_dose_date < interval_end:
                actual_end = last_dose_date
            
            # Skip if interval starts after last dose
            if last_dose_date and interval_start > last_dose_date:
                continue
            
            # Adjust start if needed
            actual_start = interval_start
            if actual_start < first_dose_date:
                actual_start = first_dose_date
            
            if actual_start > actual_end:
                continue
            
            if self.exposure_mode == "period":
                interval_records = self._generate_period_records(
                    subject, regimen, timeline, rfstdtc, 
                    actual_start, actual_end, frequency
                )
            else:
                interval_records = self._generate_daily_records(
                    subject, regimen, timeline, rfstdtc,
                    actual_start, actual_end, frequency
                )
            records.extend(interval_records)
        
        return records
    
    def _generate_intermittent_dose_records(
        self,
        subject: SubjectInfo,
        regimen: RegimenItem,
        timeline: SubjectTimeline,
        rfstdtc: Optional[date],
        first_dose_date: date,
        last_dose_date: Optional[date],
        frequency: str
    ) -> List[Dict[str, Any]]:
        """
        Generate one EX record per intermittent dose (Q2W, Q4W IV/SC infusions).
        
        Per SDTM-IG: For intermittent dosing, each administration is a discrete event
        and should be represented as a separate record with EXSTDTC = EXENDTC.
        
        Example for Q2W IV over 12 weeks: 6 records (Days 1, 15, 29, 43, 57, 71)
        """
        records = []
        dose_form = self._get_dose_form(regimen.route)
        
        # Calculate dose interval
        freq_lower = frequency.lower()
        if 'q4w' in freq_lower or 'monthly' in freq_lower:
            interval_days = 28
        elif 'q2w' in freq_lower or 'biweekly' in freq_lower:
            interval_days = 14
        elif 'q1w' in freq_lower or 'qw' in freq_lower or 'weekly' in freq_lower:
            interval_days = 7
        else:
            interval_days = 14  # Default to Q2W
        
        # Generate dose dates starting from first_dose_date
        current_date = first_dose_date
        dose_number = 0
        
        while True:
            # Stop if past last dose date
            if last_dose_date and current_date > last_dose_date:
                break
            
            # Safety limit - max 52 doses (1 year of weekly dosing)
            if dose_number >= 52:
                break
            
            dose_number += 1
            exseq = self.seq_tracker.get_next_seq('EX', subject.usubjid)
            
            # Find matching visit
            visitnum, visit = self._find_visit_for_date(current_date, timeline)
            epoch = timeline.get_epoch_for_date(current_date) or 'TREATMENT'
            
            record = {
                'STUDYID': self.spec.study_id,
                'DOMAIN': 'EX',
                'USUBJID': subject.usubjid,
                'EXSEQ': exseq,
                'EXTRT': regimen.extrt,
                'EXCAT': 'STUDY DRUG',
                'EXDOSE': regimen.dose,
                'EXDOSU': regimen.dose_unit,
                'EXDOSFRM': dose_form,
                'EXROUTE': regimen.route.value if hasattr(regimen.route, 'value') else str(regimen.route),
                'EXDOSFRQ': frequency,
                'EXSTDTC': format_iso_date(current_date),
                'EXENDTC': format_iso_date(current_date),  # Same day for IV infusion
                'EPOCH': epoch,
            }
            
            if visitnum is not None:
                record['VISITNUM'] = visitnum
                record['VISIT'] = visit or ''
            
            # Derive study days
            if rfstdtc:
                record['EXSTDY'] = derive_study_day(current_date, rfstdtc)
                record['EXENDY'] = record['EXSTDY']
            else:
                record['EXSTDY'] = ''
                record['EXENDY'] = ''
            
            records.append(record)
            
            # Move to next dose date
            current_date = add_days(current_date, interval_days)
        
        return records
    
    def _generate_visit_based_dose_records(
        self,
        subject: SubjectInfo,
        regimen: RegimenItem,
        timeline: SubjectTimeline,
        rfstdtc: Optional[date],
        first_dose_date: date,
        last_dose_date: Optional[date],
        frequency: str
    ) -> List[Dict[str, Any]]:
        """
        Generate EX records at EXACT protocol-specified visit days.
        
        This method uses the spec.visits to determine dosing days, ensuring
        that EX records match the exact protocol schedule (e.g., Days 0, 7, 21
        for loading doses, or Days 0, 14, 28, 42, 56, 70 for Q2W).
        
        Only creates records for visits where collection_flags.ex=True.
        """
        records = []
        dose_form = self._get_dose_form(regimen.route)
        
        if rfstdtc is None:
            return records
        
        # Get dosing visits from protocol spec (where ex=True)
        dosing_visits = []
        for visit in self.spec.visits:
            if visit.collection_flags and visit.collection_flags.ex:
                dosing_visits.append(visit)
        
        # Sort by nominal day to ensure correct order
        dosing_visits.sort(key=lambda v: v.nominal_day)
        
        for visit_spec in dosing_visits:
            # Calculate actual visit date from nominal day
            # nominal_day uses SDTM convention: Day 1 = rfstdtc (first day of treatment)
            # Day 1 → rfstdtc + 0 days
            # Day 15 → rfstdtc + 14 days
            # Day -14 → rfstdtc - 14 days
            if visit_spec.nominal_day >= 1:
                visit_date = add_days(rfstdtc, visit_spec.nominal_day - 1)
            else:
                # For pre-treatment visits (screening with negative day numbers)
                visit_date = add_days(rfstdtc, visit_spec.nominal_day)
            
            # Skip if before first dose date
            if visit_date < first_dose_date:
                continue
            
            # Skip if after last dose date (dropout)
            if last_dose_date and visit_date > last_dose_date:
                continue
            
            # Calculate study day
            exstdy = derive_study_day(visit_date, rfstdtc)
            
            exseq = self.seq_tracker.get_next_seq('EX', subject.usubjid)
            epoch = visit_spec.epoch or 'TREATMENT'
            
            record = {
                'STUDYID': self.spec.study_id,
                'DOMAIN': 'EX',
                'USUBJID': subject.usubjid,
                'EXSEQ': exseq,
                'EXTRT': regimen.extrt,
                'EXCAT': 'STUDY DRUG',
                'EXDOSE': regimen.dose,
                'EXDOSU': regimen.dose_unit,
                'EXDOSFRM': dose_form,
                'EXROUTE': regimen.route.value if hasattr(regimen.route, 'value') else str(regimen.route),
                'EXDOSFRQ': frequency,
                'VISITNUM': visit_spec.visitnum,
                'VISIT': visit_spec.visit,
                'EPOCH': epoch,
                'EXSTDTC': format_iso_date(visit_date),
                'EXENDTC': format_iso_date(visit_date),
                'EXSTDY': exstdy,
                'EXENDY': exstdy,
            }
            records.append(record)
        
        return records

    def _generate_visit_records(
        self,
        subject: SubjectInfo,
        regimen: RegimenItem,
        timeline: SubjectTimeline,
        rfstdtc: Optional[date],
        first_dose_date: date,
        last_dose_date: Optional[date],
        frequency: str
    ) -> List[Dict[str, Any]]:
        """
        Generate one EX record per scheduled visit where treatment is administered.
        
        Used for clinic-administered treatments like weekly/monthly injections.
        Each record has EXSTDTC = EXENDTC = visit date (single-dose administration).
        """
        records = []
        dose_form = self._get_dose_form(regimen.route)
        
        # Determine which element this regimen applies to
        element_ref = regimen.element_ref
        
        # Get visits that have EX collection and fall within the treatment period
        for visitnum, visit_date in sorted(timeline.visit_dates.items()):
            # Skip if before first dose or after last dose
            if visit_date < first_dose_date:
                continue
            if last_dose_date and visit_date > last_dose_date:
                continue
            
            # Find the visit spec to check if EX is collected
            visit_spec = None
            for v in self.spec.visits:
                if v.visitnum == visitnum:
                    visit_spec = v
                    break
            
            if visit_spec is None:
                continue
            
            # Skip if visit doesn't collect EX
            if visit_spec.collection_flags and not visit_spec.collection_flags.ex:
                continue
            
            # If element_ref specified, check if visit falls within that element
            if element_ref:
                visit_in_element = False
                
                # Use the visit's nominal day to determine element membership
                # This avoids issues with visit window drift
                visit_nominal_day = visit_spec.nominal_day if visit_spec else None
                
                # Get element's nominal day range from spec
                elem_spec = None
                cumulative_day = 1
                for etcd in self.spec.get_element_sequence_for_arm(subject.armcd):
                    elem = self.spec.get_element_by_code(etcd)
                    if elem:
                        elem_start_day = cumulative_day
                        elem_end_day = cumulative_day + elem.nominal_duration_days - 1
                        
                        if elem.etcd == element_ref:
                            # Check if visit's nominal day falls within this element
                            if visit_nominal_day is not None:
                                if elem_start_day <= visit_nominal_day <= elem_end_day:
                                    visit_in_element = True
                            else:
                                # Fallback to date-based check if no nominal day
                                for interval in timeline.element_intervals:
                                    if interval.get('etcd') == element_ref:
                                        interval_start = interval.get('start_date')
                                        interval_end = interval.get('end_date')
                                        if interval_start and interval_end:
                                            if interval_start <= visit_date <= interval_end:
                                                visit_in_element = True
                            break
                        
                        # Move to next element (screening is before Day 1)
                        if elem.epoch.upper() != 'SCREENING':
                            cumulative_day = elem_end_day + 1
                
                if not visit_in_element:
                    continue
            
            # Get epoch for the visit
            epoch = timeline.get_epoch_for_date(visit_date) or 'TREATMENT'
            
            exseq = self.seq_tracker.get_next_seq('EX', subject.usubjid)
            
            record = {
                'STUDYID': self.spec.study_id,
                'DOMAIN': 'EX',
                'USUBJID': subject.usubjid,
                'EXSEQ': exseq,
                'EXTRT': regimen.extrt,
                'EXCAT': 'STUDY DRUG',
                'EXDOSE': regimen.dose,
                'EXDOSU': regimen.dose_unit,
                'EXDOSFRM': dose_form,
                'EXROUTE': regimen.route.value if hasattr(regimen.route, 'value') else str(regimen.route),
                'EXDOSFRQ': frequency,
                'EXSTDTC': format_iso_date(visit_date),
                'EXENDTC': format_iso_date(visit_date),  # Single-dose: start = end
                'EPOCH': epoch,
                'VISITNUM': visitnum,
                'VISIT': visit_spec.visit if visit_spec else '',
            }
            
            # Derive study days
            if rfstdtc:
                study_day = derive_study_day(visit_date, rfstdtc)
                record['EXSTDY'] = study_day
                record['EXENDY'] = study_day
            else:
                record['EXSTDY'] = ''
                record['EXENDY'] = ''
            
            records.append(record)
        
        return records
    
    def _get_treatment_intervals(
        self, 
        timeline: SubjectTimeline, 
        regimen: RegimenItem
    ) -> List[tuple]:
        """
        Get treatment intervals from subject's element_intervals.
        
        Returns list of (start_date, end_date) tuples for treatment elements.
        If regimen has element_ref, only returns that element's interval.
        Otherwise, returns all TREATMENT epoch intervals.
        """
        intervals = []
        
        for interval in timeline.element_intervals:
            epoch = interval.get('epoch', '')
            etcd = interval.get('etcd', '')
            start = interval.get('start_date')
            end = interval.get('end_date')
            
            if start is None or end is None:
                continue
            
            # If regimen specifies an element, only use that element
            if regimen.element_ref:
                if etcd == regimen.element_ref:
                    intervals.append((start, end))
            else:
                # Otherwise, use all treatment elements
                if 'TREATMENT' in epoch.upper():
                    intervals.append((start, end))
        
        return intervals
    
    def _generate_period_records(
        self,
        subject: SubjectInfo,
        regimen: RegimenItem,
        timeline: SubjectTimeline,
        rfstdtc: Optional[date],
        start_date: date,
        end_date: date,
        frequency: str
    ) -> List[Dict[str, Any]]:
        """Generate consolidated period-based exposure records."""
        records = []
        
        exseq = self.seq_tracker.get_next_seq('EX', subject.usubjid)
        
        # For exposure, epoch should be TREATMENT (study drug is administered during treatment)
        # Use element epoch if specified, otherwise default to TREATMENT
        if regimen.element_ref:
            elem = self.spec.get_element_by_etcd(regimen.element_ref)
            epoch = elem.epoch if elem else 'TREATMENT'
        else:
            # Check a date within the exposure period (not the boundary)
            mid_date = add_days(start_date, 1) if start_date < end_date else start_date
            epoch = timeline.get_epoch_for_date(mid_date) or 'TREATMENT'
        
        dose_form = self._get_dose_form(regimen.route)
        
        # Find visit for start date (dispensing visit)
        visitnum, visit = self._find_visit_for_date(start_date, timeline)
        
        record = {
            'STUDYID': self.spec.study_id,
            'DOMAIN': 'EX',
            'USUBJID': subject.usubjid,
            'EXSEQ': exseq,
            'EXTRT': regimen.extrt,
            'EXCAT': 'STUDY DRUG',
            'EXDOSE': regimen.dose,
            'EXDOSU': regimen.dose_unit,
            'EXDOSFRM': dose_form,
            'EXROUTE': regimen.route.value if hasattr(regimen.route, 'value') else str(regimen.route),
            'EXDOSFRQ': frequency,
            'EXSTDTC': format_iso_date(start_date),
            'EXENDTC': format_iso_date(end_date),
            'EPOCH': epoch,
        }
        
        # Add visit info if available (dispensing visit)
        if visitnum is not None:
            record['VISITNUM'] = visitnum
            record['VISIT'] = visit or ''
        
        # Derive study days
        if rfstdtc:
            record['EXSTDY'] = derive_study_day(start_date, rfstdtc)
            record['EXENDY'] = derive_study_day(end_date, rfstdtc)
        else:
            record['EXSTDY'] = ''
            record['EXENDY'] = ''
        
        records.append(record)
        return records
    
    def _generate_daily_records(
        self,
        subject: SubjectInfo,
        regimen: RegimenItem,
        timeline: SubjectTimeline,
        rfstdtc: Optional[date],
        start_date: date,
        end_date: date,
        frequency: str
    ) -> List[Dict[str, Any]]:
        """Generate daily dose-by-dose exposure records."""
        records = []
        
        # Calculate dose dates based on frequency
        dose_dates = self._calculate_dose_dates(start_date, (end_date - start_date).days + 1, frequency, end_date)
        
        for dose_date in dose_dates:
            exseq = self.seq_tracker.get_next_seq('EX', subject.usubjid)
            
            # Find matching visit
            visitnum, visit = self._find_visit_for_date(dose_date, timeline)
            epoch = timeline.get_epoch_for_date(dose_date) or 'TREATMENT'
            
            # Derive dose form from route
            dose_form = self._get_dose_form(regimen.route)
            
            record = {
                'STUDYID': self.spec.study_id,
                'DOMAIN': 'EX',
                'USUBJID': subject.usubjid,
                'EXSEQ': exseq,
                'EXTRT': regimen.extrt,
                'EXCAT': 'STUDY DRUG',
                'EXDOSE': regimen.dose,
                'EXDOSU': regimen.dose_unit,
                'EXDOSFRM': dose_form,
                'EXROUTE': regimen.route.value if hasattr(regimen.route, 'value') else str(regimen.route),
                'EXDOSFRQ': frequency,
                'EXSTDTC': format_iso_date(dose_date),
                'EXENDTC': format_iso_date(dose_date),  # Single dose
                'EPOCH': epoch,
            }
            
            if visitnum:
                record['VISITNUM'] = visitnum
                record['VISIT'] = visit
            
            # Derive study days
            if rfstdtc:
                record['EXSTDY'] = derive_study_day(dose_date, rfstdtc)
                record['EXENDY'] = record['EXSTDY']
            else:
                record['EXSTDY'] = ''
                record['EXENDY'] = ''
            
            records.append(record)
        
        return records
    
    def _calculate_dose_dates(
        self, 
        start_date: date, 
        duration_days: int, 
        frequency: str,
        censor_date: Optional[date]
    ) -> List[date]:
        """Calculate dose dates based on frequency."""
        dates = []
        
        # Determine interval in days
        freq_lower = frequency.lower()
        if 'qd' in freq_lower or 'daily' in freq_lower:
            interval = 1
        elif 'q1w' in freq_lower or 'weekly' in freq_lower or 'qw' in freq_lower:
            interval = 7
        elif 'q2w' in freq_lower or 'biweekly' in freq_lower:
            interval = 14
        elif 'q4w' in freq_lower or 'monthly' in freq_lower:
            interval = 28
        else:
            interval = 1  # Default to daily
        
        current_date = start_date
        end_date = add_days(start_date, duration_days - 1)
        
        # Apply censor date if earlier
        if censor_date and censor_date < end_date:
            end_date = censor_date
        
        while current_date <= end_date:
            dates.append(current_date)
            current_date = add_days(current_date, interval)
        
        return dates
    
    def _find_visit_for_date(
        self, 
        dose_date: date, 
        timeline: SubjectTimeline
    ) -> tuple:
        """
        Find the visit for a given date.
        
        Only returns visit info if dose_date matches an actual scheduled visit.
        For home dosing (doses on non-visit days), returns (None, None).
        This ensures EX records only have VISIT/VISITNUM for clinic-administered doses.
        """
        for visitnum, visit_date in timeline.visit_dates.items():
            if dose_date == visit_date:
                # Get visit name from spec
                for v in self.spec.visits:
                    if v.visitnum == visitnum:
                        return visitnum, v.visit
                return visitnum, None
        
        return None, None
    
    def _get_dose_form(self, route: Route) -> str:
        """Derive dose form from route of administration."""
        route_to_form = {
            Route.ORAL: 'TABLET',
            Route.SUBLINGUAL: 'TABLET',
            Route.SUBCUTANEOUS: 'INJECTION',
            Route.INTRAVENOUS: 'INJECTION',
            Route.INTRAMUSCULAR: 'INJECTION',
            Route.TOPICAL: 'CREAM',
            Route.INHALATION: 'AEROSOL',
        }
        return route_to_form.get(route, 'UNKNOWN')
    
    def _empty_ex(self) -> pd.DataFrame:
        """Return empty EX DataFrame with correct columns."""
        return pd.DataFrame(columns=[
            'STUDYID', 'DOMAIN', 'USUBJID', 'EXSEQ', 'EXTRT', 'EXCAT',
            'EXDOSE', 'EXDOSU', 'EXDOSFRM', 'EXROUTE', 'EXDOSFRQ',
            'EXSTDTC', 'EXENDTC', 'EXSTDY', 'EXENDY', 'EPOCH', 'VISITNUM', 'VISIT'
        ])
