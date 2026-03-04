"""
SDTM Synthetic Data Generator - Adverse Events Generator

This module generates the Adverse Events (AE) dataset.
"""

from __future__ import annotations
from typing import List, Dict, Any, Optional, Set
from datetime import date
import pandas as pd

from ..spec.models import TrialDesignSpec
from ..backbone.subjects import SubjectRegistry, SubjectInfo
from ..timeline.engine import TimelineEngine, SubjectTimeline
from ..utils.rng import get_rng
from ..utils.dates import format_iso_date, parse_date, derive_study_day, add_days
from ..utils.ids import SequenceTracker


# Default adverse event library
DEFAULT_AE_LIBRARY = [
    {'aeterm': 'HEADACHE', 'aedecod': 'Headache', 'aebodsys': 'NERVOUS SYSTEM DISORDERS',
     'prob': 0.20, 'sev_dist': {'MILD': 0.7, 'MODERATE': 0.25, 'SEVERE': 0.05}},
    {'aeterm': 'NAUSEA', 'aedecod': 'Nausea', 'aebodsys': 'GASTROINTESTINAL DISORDERS',
     'prob': 0.15, 'sev_dist': {'MILD': 0.6, 'MODERATE': 0.35, 'SEVERE': 0.05}},
    {'aeterm': 'DIZZINESS', 'aedecod': 'Dizziness', 'aebodsys': 'NERVOUS SYSTEM DISORDERS',
     'prob': 0.12, 'sev_dist': {'MILD': 0.65, 'MODERATE': 0.3, 'SEVERE': 0.05}},
    {'aeterm': 'FATIGUE', 'aedecod': 'Fatigue', 'aebodsys': 'GENERAL DISORDERS',
     'prob': 0.18, 'sev_dist': {'MILD': 0.55, 'MODERATE': 0.4, 'SEVERE': 0.05}},
    {'aeterm': 'DIARRHEA', 'aedecod': 'Diarrhoea', 'aebodsys': 'GASTROINTESTINAL DISORDERS',
     'prob': 0.10, 'sev_dist': {'MILD': 0.5, 'MODERATE': 0.4, 'SEVERE': 0.1}},
    {'aeterm': 'INSOMNIA', 'aedecod': 'Insomnia', 'aebodsys': 'PSYCHIATRIC DISORDERS',
     'prob': 0.08, 'sev_dist': {'MILD': 0.6, 'MODERATE': 0.35, 'SEVERE': 0.05}},
    {'aeterm': 'BACK PAIN', 'aedecod': 'Back pain', 'aebodsys': 'MUSCULOSKELETAL DISORDERS',
     'prob': 0.08, 'sev_dist': {'MILD': 0.5, 'MODERATE': 0.4, 'SEVERE': 0.1}},
    {'aeterm': 'UPPER RESPIRATORY TRACT INFECTION', 'aedecod': 'Upper respiratory tract infection', 
     'aebodsys': 'INFECTIONS AND INFESTATIONS',
     'prob': 0.12, 'sev_dist': {'MILD': 0.55, 'MODERATE': 0.4, 'SEVERE': 0.05}},
    {'aeterm': 'CONSTIPATION', 'aedecod': 'Constipation', 'aebodsys': 'GASTROINTESTINAL DISORDERS',
     'prob': 0.07, 'sev_dist': {'MILD': 0.65, 'MODERATE': 0.3, 'SEVERE': 0.05}},
    {'aeterm': 'RASH', 'aedecod': 'Rash', 'aebodsys': 'SKIN AND SUBCUTANEOUS TISSUE DISORDERS',
     'prob': 0.05, 'sev_dist': {'MILD': 0.6, 'MODERATE': 0.3, 'SEVERE': 0.1}},
    # Serious AEs that can be fatal
    {'aeterm': 'MYOCARDIAL INFARCTION', 'aedecod': 'Myocardial infarction', 
     'aebodsys': 'CARDIAC DISORDERS',
     'prob': 0.01, 'sev_dist': {'MODERATE': 0.2, 'SEVERE': 0.8}, 'can_be_fatal': True},
    {'aeterm': 'PNEUMONIA', 'aedecod': 'Pneumonia', 'aebodsys': 'INFECTIONS AND INFESTATIONS',
     'prob': 0.02, 'sev_dist': {'MODERATE': 0.5, 'SEVERE': 0.5}, 'can_be_fatal': True},
    {'aeterm': 'SEPSIS', 'aedecod': 'Sepsis', 'aebodsys': 'INFECTIONS AND INFESTATIONS',
     'prob': 0.005, 'sev_dist': {'SEVERE': 1.0}, 'can_be_fatal': True},
]


class AdverseEventsGenerator:
    """
    Generates the Adverse Events (AE) dataset.
    
    Records adverse events occurring during study participation.
    
    Features:
    - AELINKID for cross-domain linking (to CM, DS via RELREC)
    - AESDTH flag for AEs resulting in death
    - Configurable fatal AE rate
    """
    
    def __init__(self, 
                 spec: TrialDesignSpec, 
                 registry: SubjectRegistry,
                 timeline_engine: TimelineEngine,
                 clean_mode: bool = True,
                 allow_deaths: bool = True,
                 death_rate: float = 0.02):
        """
        Initialize the generator.
        
        Args:
            spec: Trial design specification
            registry: Subject registry
            timeline_engine: Timeline engine with subject timelines
            clean_mode: If True, ensures cross-domain consistency
            allow_deaths: If True, allows FATAL AEs (with cross-domain updates)
            death_rate: Probability of a subject having a fatal AE (default 2%)
        """
        self.spec = spec
        self.registry = registry
        self.timeline_engine = timeline_engine
        self.rng = get_rng()
        self.seq_tracker = SequenceTracker()
        self.clean_mode = clean_mode
        self.allow_deaths = allow_deaths
        self.death_rate = death_rate
        
        # Track subjects with AEs (for DS coupling validation)
        self.subjects_with_ae: Set[str] = set()
        self.fatal_ae_subjects: Dict[str, date] = {}  # usubjid -> death date
        
        # Link ID counter for AELINKID
        self.link_id_counter: Dict[str, int] = {}  # usubjid -> counter
        
        # Use spec-driven configuration
        ae_model = spec.ae_model
        
        # Build AE library from spec if provided, otherwise use defaults
        if ae_model.ae_term_library:
            # Convert spec's AE term library to generator format
            total_weight = sum(t.weight for t in ae_model.ae_term_library)
            self.ae_library = []
            for term in ae_model.ae_term_library:
                prob = term.weight / total_weight if total_weight > 0 else 0.1
                self.ae_library.append({
                    'aeterm': term.aeterm,
                    'aedecod': term.aedecod,
                    'aebodsys': term.aebodsys,
                    'prob': prob,
                    'sev_dist': {'MILD': 0.6, 'MODERATE': 0.35, 'SEVERE': 0.05},
                })
            # Always add some serious AEs for realism
            self.ae_library.extend([
                {'aeterm': 'PNEUMONIA', 'aedecod': 'Pneumonia', 'aebodsys': 'INFECTIONS AND INFESTATIONS',
                 'prob': 0.02, 'sev_dist': {'MODERATE': 0.5, 'SEVERE': 0.5}, 'can_be_fatal': True},
                {'aeterm': 'SEPSIS', 'aedecod': 'Sepsis', 'aebodsys': 'INFECTIONS AND INFESTATIONS',
                 'prob': 0.005, 'sev_dist': {'SEVERE': 1.0}, 'can_be_fatal': True},
            ])
        else:
            self.ae_library = DEFAULT_AE_LIBRARY
        
        self.ae_rate_multiplier = ae_model.ae_rate_multiplier
        
        # Relationship distribution from spec
        self.rel_dist = ae_model.relationship_dist.copy()
        
        # Outcome distribution from spec
        # In clean_mode or if enable_fatal is False, ensure FATAL is not in distribution
        if clean_mode or not ae_model.enable_fatal:
            self.outcome_dist = {k: v for k, v in ae_model.outcome_dist.items() if k != 'FATAL'}
            # Normalize distribution
            total = sum(self.outcome_dist.values())
            if total > 0:
                self.outcome_dist = {k: v/total for k, v in self.outcome_dist.items()}
        else:
            self.outcome_dist = ae_model.outcome_dist.copy()
    
    def generate(self) -> pd.DataFrame:
        """
        Generate AE dataset.
        
        Features:
        - Ensures subjects with DS dropout_reason="ADVERSE EVENT" have at least one AE
        - Adds AELINKID for cross-domain linking
        - Adds AESDTH flag for fatal AEs
        - Optionally generates fatal AEs (with cross-domain consistency)
        
        Returns:
            AE DataFrame
        """
        records = []
        
        # Determine which subjects will have fatal AEs
        fatal_subject_ids = set()
        if self.allow_deaths:
            enrolled = list(self.registry.get_enrolled_subjects())
            num_deaths = max(1, int(len(enrolled) * self.death_rate))
            # Select random subjects for fatal AE
            candidates = [s for s in enrolled if s.dropout_reason != "ADVERSE EVENT"]
            if candidates and num_deaths > 0:
                # Shuffle and take first N
                shuffled = self.rng.shuffle(candidates.copy())
                fatal_subject_ids = {s.usubjid for s in shuffled[:min(num_deaths, len(candidates))]}
        
        # First pass: generate AEs for all subjects
        for subject in self.registry.get_enrolled_subjects():
            # Check if this subject should have a fatal AE
            generate_fatal = subject.usubjid in fatal_subject_ids
            subject_records = self._generate_subject_ae(subject, generate_fatal=generate_fatal)
            if subject_records:
                self.subjects_with_ae.add(subject.usubjid)
            records.extend(subject_records)
        
        # Second pass: ensure subjects with DS "ADVERSE EVENT" reason have AEs
        for subject in self.registry.get_enrolled_subjects():
            if subject.dropout_reason == "ADVERSE EVENT" and subject.usubjid not in self.subjects_with_ae:
                # Force generate at least one AE for this subject
                forced_ae = self._generate_forced_ae(subject)
                if forced_ae:
                    records.extend(forced_ae)
                    self.subjects_with_ae.add(subject.usubjid)
        
        if not records:
            return self._empty_ae()
        
        df = pd.DataFrame(records)
        
        # Sort by USUBJID, AESTDTC, AESEQ
        df = df.sort_values(['USUBJID', 'AESTDTC', 'AESEQ']).reset_index(drop=True)
        
        # Column order per SDTM-IG
        cols = ['STUDYID', 'DOMAIN', 'USUBJID', 'AESEQ', 'AELNKID', 'AETERM', 'AEDECOD', 
                'AEBODSYS', 'AESEV', 'AESER', 'AESDTH', 'AEREL', 'AEOUT', 'AEACN',
                'AESTDTC', 'AEENDTC', 'AESTDY', 'AEENDY', 'EPOCH']
        
        return df[[c for c in cols if c in df.columns]]
    
    def _get_next_link_id(self, usubjid: str) -> str:
        """Generate next AELINKID for a subject."""
        if usubjid not in self.link_id_counter:
            self.link_id_counter[usubjid] = 0
        self.link_id_counter[usubjid] += 1
        return f"AE{self.link_id_counter[usubjid]:03d}"
    
    def _generate_forced_ae(self, subject: SubjectInfo) -> List[Dict[str, Any]]:
        """
        Generate a forced AE for subjects with DS dropout_reason="ADVERSE EVENT".
        
        Creates a moderate/severe AE that leads to discontinuation.
        """
        timeline = self.timeline_engine.get_subject_timeline(subject.usubjid)
        if timeline is None:
            return []
        
        rfstdtc = parse_date(subject.rfstdtc) if subject.rfstdtc else None
        if rfstdtc is None:
            return []
        
        censor_date = timeline.censor_date or timeline.end_date
        
        # Generate AE near end of participation (causing discontinuation)
        if censor_date:
            # AE occurs 1-14 days before discontinuation
            days_before = min(14, max(1, (censor_date - rfstdtc).days - 1))
            onset_days = self.rng.randint(1, days_before) if days_before > 1 else 1
            onset_date = add_days(censor_date, -onset_days)
        else:
            onset_date = add_days(rfstdtc, self.rng.randint(7, 28))
        
        aeseq = self.seq_tracker.get_next_seq('AE', subject.usubjid)
        aelnkid = self._get_next_link_id(subject.usubjid)
        
        # Pick a random AE type
        ae_template = self.rng.choice(self.ae_library)
        
        # Force severity to MODERATE or SEVERE (leading to discontinuation)
        severity = self.rng.choice(['MODERATE', 'SEVERE'])
        is_serious = severity == 'SEVERE' or self.rng.bernoulli(0.3)
        
        # Relationship - more likely to be related since it caused discontinuation
        relationship = self.rng.choice(['POSSIBLY RELATED', 'PROBABLY RELATED', 'RELATED'])
        
        # Outcome - ongoing since it caused discontinuation
        outcome = 'NOT RECOVERED/NOT RESOLVED'
        end_date = None
        
        epoch = timeline.get_epoch_for_date(onset_date) or 'TREATMENT'
        
        record = {
            'STUDYID': self.spec.study_id,
            'DOMAIN': 'AE',
            'USUBJID': subject.usubjid,
            'AESEQ': aeseq,
            'AELNKID': aelnkid,
            'AETERM': ae_template['aeterm'],
            'AEDECOD': ae_template['aedecod'],
            'AEBODSYS': ae_template['aebodsys'],
            'AESEV': severity,
            'AESER': 'Y' if is_serious else 'N',
            'AESDTH': 'N',  # Forced AEs are not fatal (they cause withdrawal, not death)
            'AEREL': relationship,
            'AEOUT': outcome,
            'AEACN': 'DRUG WITHDRAWN',
            'AESTDTC': format_iso_date(onset_date),
            'AEENDTC': '',
            'EPOCH': epoch,
        }
        
        if rfstdtc:
            record['AESTDY'] = derive_study_day(onset_date, rfstdtc)
            record['AEENDY'] = ''
        
        return [record]
    
    def _generate_subject_ae(self, subject: SubjectInfo, generate_fatal: bool = False) -> List[Dict[str, Any]]:
        """
        Generate AE records for a single subject.
        
        Args:
            subject: Subject info
            generate_fatal: If True, generate a fatal AE for this subject
        """
        records = []
        
        # Get timeline
        timeline = self.timeline_engine.get_subject_timeline(subject.usubjid)
        if timeline is None:
            return records
        
        rfstdtc = parse_date(subject.rfstdtc) if subject.rfstdtc else None
        first_dose = timeline.first_dose_date
        censor_date = timeline.censor_date
        
        if first_dose is None:
            return records
        
        # Calculate participation duration
        if censor_date:
            study_days = (censor_date - first_dose).days
        else:
            study_days = 84  # Default 12 weeks
        
        # Generate AEs for each potential event type
        for ae_template in self.ae_library:
            # Check if this AE occurs for this subject
            # Probability scaled by study duration
            duration_factor = min(study_days / 84.0, 1.5)  # Cap at 1.5x
            prob = ae_template['prob'] * self.ae_rate_multiplier * duration_factor
            
            if self.rng.bernoulli(prob):
                ae_record = self._generate_single_ae(
                    subject, ae_template, timeline, rfstdtc, first_dose, censor_date
                )
                records.append(ae_record)
        
        # Generate fatal AE if requested
        if generate_fatal:
            fatal_record = self._generate_fatal_ae(subject, timeline, rfstdtc, first_dose, censor_date)
            if fatal_record:
                records.append(fatal_record)
        
        return records
    
    def _generate_fatal_ae(
        self,
        subject: SubjectInfo,
        timeline: SubjectTimeline,
        rfstdtc: Optional[date],
        first_dose: date,
        censor_date: Optional[date]
    ) -> Optional[Dict[str, Any]]:
        """Generate a fatal AE record."""
        # Select a serious AE template that can be fatal
        fatal_templates = [t for t in self.ae_library if t.get('can_be_fatal', False)]
        if not fatal_templates:
            # Fallback to any serious AE
            fatal_templates = [t for t in self.ae_library 
                            if t.get('sev_dist', {}).get('SEVERE', 0) > 0.3]
        if not fatal_templates:
            fatal_templates = self.ae_library
        
        ae_template = self.rng.choice(fatal_templates)
        
        aeseq = self.seq_tracker.get_next_seq('AE', subject.usubjid)
        aelnkid = self._get_next_link_id(subject.usubjid)
        
        # Fatal AE occurs in the study period
        max_days = (censor_date - first_dose).days if censor_date else 84
        # Fatal AE typically later in study (to give some exposure time)
        onset_day = self.rng.randint(max(7, max_days // 4), max(14, max_days))
        onset_date = add_days(first_dose, onset_day)
        
        # Death occurs within 0-3 days of AE onset
        death_delay = self.rng.randint(0, 3)
        death_date = add_days(onset_date, death_delay)
        
        # Track for cross-domain updates
        self.fatal_ae_subjects[subject.usubjid] = death_date
        
        epoch = timeline.get_epoch_for_date(onset_date) or 'TREATMENT'
        
        record = {
            'STUDYID': self.spec.study_id,
            'DOMAIN': 'AE',
            'USUBJID': subject.usubjid,
            'AESEQ': aeseq,
            'AELNKID': aelnkid,
            'AETERM': ae_template['aeterm'],
            'AEDECOD': ae_template['aedecod'],
            'AEBODSYS': ae_template['aebodsys'],
            'AESEV': 'SEVERE',  # Fatal AEs are always severe
            'AESER': 'Y',  # Fatal AEs are always serious
            'AESDTH': 'Y',  # AE resulted in death
            'AEREL': self.rng.choice(['POSSIBLY RELATED', 'PROBABLY RELATED', 'NOT RELATED']),
            'AEOUT': 'FATAL',
            'AEACN': 'NOT APPLICABLE',  # No action for fatal outcome
            'AESTDTC': format_iso_date(onset_date),
            'AEENDTC': format_iso_date(death_date),
            'EPOCH': epoch,
        }
        
        if rfstdtc:
            record['AESTDY'] = derive_study_day(onset_date, rfstdtc)
            record['AEENDY'] = derive_study_day(death_date, rfstdtc)
        
        return record
    
    def _generate_single_ae(
        self,
        subject: SubjectInfo,
        ae_template: Dict[str, Any],
        timeline: SubjectTimeline,
        rfstdtc: Optional[date],
        first_dose: date,
        censor_date: Optional[date]
    ) -> Dict[str, Any]:
        """Generate a single AE record with AELINKID for cross-domain linking."""
        aeseq = self.seq_tracker.get_next_seq('AE', subject.usubjid)
        aelnkid = self._get_next_link_id(subject.usubjid)
        
        # Generate onset date (between first dose and censor)
        max_days = (censor_date - first_dose).days if censor_date else 84
        onset_day = self.rng.randint(0, max(1, max_days))
        onset_date = add_days(first_dose, onset_day)
        
        # Generate severity
        sev_dist = ae_template.get('sev_dist', {'MILD': 0.6, 'MODERATE': 0.3, 'SEVERE': 0.1})
        severity = self.rng.sample_from_distribution(sev_dist, n=1)[0]
        
        # Determine if serious - must be logically consistent with severity
        if severity == 'SEVERE':
            is_serious = self.rng.bernoulli(0.75)
        elif severity == 'MODERATE':
            is_serious = self.rng.bernoulli(0.08)
        else:
            is_serious = self.rng.bernoulli(0.01)
        
        # Generate relationship to study drug
        relationship = self.rng.sample_from_distribution(self.rel_dist, n=1)[0]
        
        # Generate outcome
        outcome = self.rng.sample_from_distribution(self.outcome_dist, n=1)[0]
        
        # Initialize death flag
        is_death = False
        
        # Generate end date based on outcome
        if outcome in ['RECOVERED/RESOLVED', 'RECOVERED/RESOLVED WITH SEQUELAE']:
            duration = self.rng.randint(1, 30)
            end_date = add_days(onset_date, duration)
            if censor_date and end_date > censor_date:
                end_date = censor_date
        elif outcome == 'RECOVERING/RESOLVING':
            end_date = censor_date if censor_date else None
        elif outcome == 'FATAL':
            death_delay = self.rng.randint(0, 2)
            end_date = add_days(onset_date, death_delay)
            self.fatal_ae_subjects[subject.usubjid] = end_date
            is_serious = True
            is_death = True
        else:
            end_date = None
        
        # Determine action taken based on relationship AND severity
        if relationship in ['NOT RELATED', 'UNLIKELY RELATED']:
            action = 'DOSE NOT CHANGED'
        else:
            if severity == 'SEVERE':
                action = self.rng.choice(['DRUG INTERRUPTED', 'DOSE REDUCED', 'DRUG WITHDRAWN'])
            elif severity == 'MODERATE':
                action = self.rng.choice(['DRUG INTERRUPTED', 'DOSE REDUCED', 'DOSE NOT CHANGED'])
            else:
                action = self.rng.choice(['DOSE NOT CHANGED', 'DOSE REDUCED'])
        
        epoch = timeline.get_epoch_for_date(onset_date) or 'TREATMENT'
        
        record = {
            'STUDYID': self.spec.study_id,
            'DOMAIN': 'AE',
            'USUBJID': subject.usubjid,
            'AESEQ': aeseq,
            'AELNKID': aelnkid,
            'AETERM': ae_template['aeterm'],
            'AEDECOD': ae_template['aedecod'],
            'AEBODSYS': ae_template['aebodsys'],
            'AESEV': severity,
            'AESER': 'Y' if is_serious else 'N',
            'AESDTH': 'Y' if is_death else 'N',
            'AEREL': relationship,
            'AEOUT': outcome,
            'AEACN': action,
            'AESTDTC': format_iso_date(onset_date),
            'AEENDTC': format_iso_date(end_date) if end_date else '',
            'EPOCH': epoch,
        }
        
        if rfstdtc:
            record['AESTDY'] = derive_study_day(onset_date, rfstdtc)
            if end_date:
                record['AEENDY'] = derive_study_day(end_date, rfstdtc)
            else:
                record['AEENDY'] = ''
        else:
            record['AESTDY'] = ''
            record['AEENDY'] = ''
        
        return record
    
    def _empty_ae(self) -> pd.DataFrame:
        """Return empty AE DataFrame with correct columns."""
        return pd.DataFrame(columns=[
            'STUDYID', 'DOMAIN', 'USUBJID', 'AESEQ', 'AELNKID', 'AETERM', 'AEDECOD',
            'AEBODSYS', 'AESEV', 'AESER', 'AESDTH', 'AEREL', 'AEOUT', 'AEACN',
            'AESTDTC', 'AEENDTC', 'AESTDY', 'AEENDY', 'EPOCH'
        ])
