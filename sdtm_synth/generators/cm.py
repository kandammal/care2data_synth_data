"""
SDTM Synthetic Data Generator - Concomitant Medications Generator

This module generates the Concomitant Medications (CM) dataset.
"""

from __future__ import annotations
from typing import List, Dict, Any, Optional
from datetime import date, timedelta
import pandas as pd

from ..spec.models import TrialDesignSpec
from ..backbone.subjects import SubjectRegistry, SubjectInfo
from ..timeline.engine import TimelineEngine, SubjectTimeline
from ..utils.rng import get_rng
from ..utils.dates import format_iso_date, parse_date, derive_study_day, add_days
from ..utils.ids import SequenceTracker
from ..terminology.controlled_terminology import (
    FREQUENCY_CT, UNIT_CT, ROUTE_CT, normalize_unit, normalize_frequency
)


# Default medication library - using CDISC CT values
DEFAULT_MEDICATION_LIBRARY = [
    {'cmtrt': 'ACETAMINOPHEN', 'cmdecod': 'PARACETAMOL', 'cmcat': 'ANALGESIC', 
     'cmdose': 500, 'cmdosu': 'mg', 'cmroute': 'ORAL', 'cmdosfrq': 'PRN', 'ongoing_prob': 0.3},
    {'cmtrt': 'IBUPROFEN', 'cmdecod': 'IBUPROFEN', 'cmcat': 'NSAID',
     'cmdose': 400, 'cmdosu': 'mg', 'cmroute': 'ORAL', 'cmdosfrq': 'TID', 'ongoing_prob': 0.25},
    {'cmtrt': 'METFORMIN', 'cmdecod': 'METFORMIN', 'cmcat': 'ANTIDIABETIC',
     'cmdose': 500, 'cmdosu': 'mg', 'cmroute': 'ORAL', 'cmdosfrq': 'BID', 'ongoing_prob': 0.9},
    {'cmtrt': 'LISINOPRIL', 'cmdecod': 'LISINOPRIL', 'cmcat': 'ANTIHYPERTENSIVE',
     'cmdose': 10, 'cmdosu': 'mg', 'cmroute': 'ORAL', 'cmdosfrq': 'QD', 'ongoing_prob': 0.85},
    {'cmtrt': 'ATORVASTATIN', 'cmdecod': 'ATORVASTATIN', 'cmcat': 'LIPID LOWERING',
     'cmdose': 20, 'cmdosu': 'mg', 'cmroute': 'ORAL', 'cmdosfrq': 'QD', 'ongoing_prob': 0.9},
    {'cmtrt': 'OMEPRAZOLE', 'cmdecod': 'OMEPRAZOLE', 'cmcat': 'PROTON PUMP INHIBITOR',
     'cmdose': 20, 'cmdosu': 'mg', 'cmroute': 'ORAL', 'cmdosfrq': 'QD', 'ongoing_prob': 0.7},
    {'cmtrt': 'AMLODIPINE', 'cmdecod': 'AMLODIPINE', 'cmcat': 'CALCIUM CHANNEL BLOCKER',
     'cmdose': 5, 'cmdosu': 'mg', 'cmroute': 'ORAL', 'cmdosfrq': 'QD', 'ongoing_prob': 0.85},
    {'cmtrt': 'SERTRALINE', 'cmdecod': 'SERTRALINE', 'cmcat': 'ANTIDEPRESSANT',
     'cmdose': 50, 'cmdosu': 'mg', 'cmroute': 'ORAL', 'cmdosfrq': 'QD', 'ongoing_prob': 0.75},
    {'cmtrt': 'LEVOTHYROXINE', 'cmdecod': 'LEVOTHYROXINE', 'cmcat': 'THYROID HORMONE',
     'cmdose': 50, 'cmdosu': 'ug', 'cmroute': 'ORAL', 'cmdosfrq': 'QD', 'ongoing_prob': 0.95},
    {'cmtrt': 'MULTIVITAMIN', 'cmdecod': 'VITAMINS', 'cmcat': 'SUPPLEMENT',
     'cmdose': 1, 'cmdosu': 'TABLET', 'cmroute': 'ORAL', 'cmdosfrq': 'QD', 'ongoing_prob': 0.6},  # TABLET per CDISC CT
]


class ConcomitantMedicationsGenerator:
    """
    Generates the Concomitant Medications (CM) dataset.
    
    Records prior and concomitant medications with timing relative to study.
    Uses CDISC Controlled Terminology for all coded fields.
    """
    
    def __init__(self, 
                 spec: TrialDesignSpec, 
                 registry: SubjectRegistry,
                 timeline_engine: Optional[TimelineEngine] = None):
        """
        Initialize the generator.
        
        Args:
            spec: Trial design specification
            registry: Subject registry
            timeline_engine: Optional timeline engine for date bounds
        """
        self.spec = spec
        self.registry = registry
        self.timeline_engine = timeline_engine
        self.rng = get_rng()
        self.seq_tracker = SequenceTracker()
        
        # Default values
        self.n_medications_mean = 2.5
        self.n_medications_sd = 1.5
        self.capture_window_years = 1
        self.medication_library = DEFAULT_MEDICATION_LIBRARY
    
    def generate(self) -> pd.DataFrame:
        """
        Generate CM dataset.
        
        Returns:
            CM DataFrame
        """
        records = []
        
        for subject in self.registry.get_all_subjects():
            subject_records = self._generate_subject_cm(subject)
            records.extend(subject_records)
        
        if not records:
            return self._empty_cm()
        
        df = pd.DataFrame(records)
        
        # Sort by USUBJID, CMSEQ
        df = df.sort_values(['USUBJID', 'CMSEQ']).reset_index(drop=True)
        
        cols = ['STUDYID', 'DOMAIN', 'USUBJID', 'CMSEQ', 'CMTRT', 'CMDECOD', 'CMCAT',
                'CMDOSE', 'CMDOSU', 'CMROUTE', 'CMDOSFRQ',
                'CMSTDTC', 'CMENDTC', 'CMENRF', 'CMSTDY', 'CMENDY', 'EPOCH']
        
        return df[[c for c in cols if c in df.columns]]
    
    def _generate_subject_cm(self, subject: SubjectInfo) -> List[Dict[str, Any]]:
        """Generate CM records for a single subject."""
        records = []
        
        # Determine number of medications
        n_meds = max(0, int(self.rng.normal(
            self.n_medications_mean,
            self.n_medications_sd
        )))
        
        if n_meds == 0:
            return records
        
        # Select medications from library
        if len(self.medication_library) < n_meds:
            n_meds = len(self.medication_library)
        
        selected_meds = self.rng.choice(
            self.medication_library, 
            size=n_meds, 
            replace=False
        )
        
        # Get reference dates
        consent_date = parse_date(subject.rficdtc) if subject.rficdtc else None
        rfstdtc = parse_date(subject.rfstdtc) if subject.rfstdtc else None
        rfendtc = parse_date(subject.rfendtc) if subject.rfendtc else None
        rfpendtc = parse_date(subject.rfpendtc) if subject.rfpendtc else None
        
        # Use rfpendtc as censor date if available, else rfendtc
        censor_date = rfpendtc or rfendtc
        
        if consent_date is None:
            return records
        
        for med in selected_meds:
            cmseq = self.seq_tracker.get_next_seq('CM', subject.usubjid)
            
            # Generate start date (within capture window before consent or after)
            capture_days = self.capture_window_years * 365
            
            # 60% start before consent, 40% start during study
            if self.rng.bernoulli(0.6):
                start_offset = self.rng.randint(30, capture_days)
                start_date = add_days(consent_date, -start_offset)
            else:
                if rfstdtc:
                    max_start = (censor_date - rfstdtc).days if censor_date else 84
                    start_offset = self.rng.randint(0, max(1, max_start))
                    start_date = add_days(rfstdtc, start_offset)
                else:
                    start_date = consent_date
            
            # Determine if ongoing based on probability
            is_ongoing = self.rng.bernoulli(med.get('ongoing_prob', 0.5))
            
            # SD0021 FIX: Properly handle ongoing vs ended medications
            if is_ongoing:
                # Medication is ongoing - no end date, set CMENRF='ONGOING'
                end_date = None
                cmenrf = 'ONGOING'
            else:
                # Medication stopped - calculate end date
                duration = self.rng.randint(7, 180)
                end_date = add_days(start_date, duration)
                
                # SD1204 FIX: Cap end date at RFPENDTC/censor date
                if censor_date and end_date > censor_date:
                    end_date = censor_date
                
                # Determine CMENRF based on when it ended relative to study
                if rfstdtc and end_date < rfstdtc:
                    cmenrf = 'BEFORE'
                else:
                    cmenrf = ''  # Ended during study, ENDTC is populated
            
            # Determine epoch
            if rfstdtc and start_date >= rfstdtc:
                epoch = 'TREATMENT'
            else:
                epoch = 'SCREENING'
            
            # Use CDISC CT for units and frequency
            cmdosu = normalize_unit(med.get('cmdosu', 'mg'))
            cmdosfrq = normalize_frequency(med.get('cmdosfrq', 'QD'))
            
            record = {
                'STUDYID': self.spec.study_id,
                'DOMAIN': 'CM',
                'USUBJID': subject.usubjid,
                'CMSEQ': cmseq,
                'CMTRT': med.get('cmtrt', 'UNKNOWN'),
                'CMDECOD': med.get('cmdecod', med.get('cmtrt', 'UNKNOWN')),
                'CMCAT': med.get('cmcat', 'GENERAL'),
                'CMDOSE': med.get('cmdose', ''),
                'CMDOSU': cmdosu,
                'CMROUTE': med.get('cmroute', 'ORAL'),
                'CMDOSFRQ': cmdosfrq,
                'CMSTDTC': format_iso_date(start_date),
                'CMENDTC': format_iso_date(end_date) if end_date else '',
                'CMENRF': cmenrf,
                'EPOCH': epoch,
            }
            
            # Derive study days
            if rfstdtc:
                record['CMSTDY'] = derive_study_day(start_date, rfstdtc)
                if end_date:
                    record['CMENDY'] = derive_study_day(end_date, rfstdtc)
                else:
                    record['CMENDY'] = ''
            else:
                record['CMSTDY'] = ''
                record['CMENDY'] = ''
            
            records.append(record)
        
        return records
    
    def _empty_cm(self) -> pd.DataFrame:
        """Return empty CM DataFrame with correct columns."""
        return pd.DataFrame(columns=[
            'STUDYID', 'DOMAIN', 'USUBJID', 'CMSEQ', 'CMTRT', 'CMDECOD', 'CMCAT',
            'CMDOSE', 'CMDOSU', 'CMROUTE', 'CMDOSFRQ',
            'CMSTDTC', 'CMENDTC', 'CMENRF', 'CMSTDY', 'CMENDY', 'EPOCH'
        ])
