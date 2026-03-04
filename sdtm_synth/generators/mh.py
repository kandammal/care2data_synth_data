"""
SDTM Synthetic Data Generator - Medical History Generator

This module generates the Medical History (MH) dataset.
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


# Default condition library for medical history
DEFAULT_CONDITION_LIBRARY = [
    {'term': 'HYPERTENSION', 'category': 'CARDIOVASCULAR', 'ongoing_prob': 0.8},
    {'term': 'TYPE 2 DIABETES MELLITUS', 'category': 'METABOLIC', 'ongoing_prob': 0.85},
    {'term': 'HYPERLIPIDEMIA', 'category': 'METABOLIC', 'ongoing_prob': 0.75},
    {'term': 'DEPRESSION', 'category': 'PSYCHIATRIC', 'ongoing_prob': 0.5},
    {'term': 'ANXIETY', 'category': 'PSYCHIATRIC', 'ongoing_prob': 0.45},
    {'term': 'ASTHMA', 'category': 'RESPIRATORY', 'ongoing_prob': 0.6},
    {'term': 'GASTROESOPHAGEAL REFLUX DISEASE', 'category': 'GASTROINTESTINAL', 'ongoing_prob': 0.55},
    {'term': 'OSTEOARTHRITIS', 'category': 'MUSCULOSKELETAL', 'ongoing_prob': 0.7},
    {'term': 'CHRONIC BACK PAIN', 'category': 'MUSCULOSKELETAL', 'ongoing_prob': 0.65},
    {'term': 'MIGRAINE', 'category': 'NEUROLOGICAL', 'ongoing_prob': 0.4},
    {'term': 'HYPOTHYROIDISM', 'category': 'ENDOCRINE', 'ongoing_prob': 0.9},
    {'term': 'ALLERGIC RHINITIS', 'category': 'IMMUNE', 'ongoing_prob': 0.5},
    {'term': 'OBESITY', 'category': 'METABOLIC', 'ongoing_prob': 0.85},
    {'term': 'SLEEP APNEA', 'category': 'RESPIRATORY', 'ongoing_prob': 0.7},
    {'term': 'CORONARY ARTERY DISEASE', 'category': 'CARDIOVASCULAR', 'ongoing_prob': 0.9},
]


class MedicalHistoryGenerator:
    """
    Generates the Medical History (MH) dataset.
    
    Medical history records prior medical conditions that may:
    - Have resolved before the study
    - Be ongoing at study start
    - Continue through the study
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
        
        # Use defaults from spec or fallback
        if hasattr(spec, 'medical_history_model_defaults') and spec.medical_history_model_defaults:
            self.defaults = spec.medical_history_model_defaults
        else:
            self.defaults = None
        
        # Default values
        self.n_conditions_mean = 2.0
        self.n_conditions_sd = 1.5
        self.capture_window_years = 5
        self.allow_ongoing = True
        self.condition_library = DEFAULT_CONDITION_LIBRARY
    
    def generate(self) -> pd.DataFrame:
        """
        Generate MH dataset.
        
        Returns:
            MH DataFrame
        """
        records = []
        
        for subject in self.registry.get_all_subjects():
            subject_records = self._generate_subject_mh(subject)
            records.extend(subject_records)
        
        if not records:
            return self._empty_mh()
        
        df = pd.DataFrame(records)
        
        # Sort by USUBJID, MHSEQ
        df = df.sort_values(['USUBJID', 'MHSEQ']).reset_index(drop=True)
        
        cols = ['STUDYID', 'DOMAIN', 'USUBJID', 'MHSEQ', 'MHTERM', 'MHDECOD', 'MHCAT', 'MHBODSYS',
                'MHSTDTC', 'MHENDTC', 'MHENRF', 'MHSTDY', 'MHENDY', 'EPOCH']
        
        return df[[c for c in cols if c in df.columns]]
    
    def _generate_subject_mh(self, subject: SubjectInfo) -> List[Dict[str, Any]]:
        """Generate MH records for a single subject."""
        records = []
        
        # Determine number of conditions
        n_conditions = max(0, int(self.rng.normal(
            self.n_conditions_mean,
            self.n_conditions_sd
        )))
        
        if n_conditions == 0:
            return records
        
        # Select conditions from library
        if len(self.condition_library) < n_conditions:
            n_conditions = len(self.condition_library)
        
        selected_conditions = self.rng.choice(
            self.condition_library, 
            size=n_conditions, 
            replace=False
        )
        
        # Get reference dates
        consent_date = parse_date(subject.rficdtc) if subject.rficdtc else None
        rfstdtc = parse_date(subject.rfstdtc) if subject.rfstdtc else None
        
        if consent_date is None:
            return records
        
        for condition in selected_conditions:
            mhseq = self.seq_tracker.get_next_seq('MH', subject.usubjid)
            
            # Generate start date (within capture window before consent)
            capture_days = self.capture_window_years * 365
            start_offset = self.rng.randint(30, capture_days)
            start_date = add_days(consent_date, -start_offset)
            
            # Determine if ongoing
            is_ongoing = self.rng.bernoulli(condition.get('ongoing_prob', 0.5))
            
            if is_ongoing and self.allow_ongoing:
                end_date = None
                mhenrf = 'DURING'
            else:
                # Condition resolved before consent
                resolution_offset = self.rng.randint(7, start_offset - 7)
                end_date = add_days(consent_date, -resolution_offset)
                mhenrf = 'BEFORE'
            
            record = {
                'STUDYID': self.spec.study_id,
                'DOMAIN': 'MH',
                'USUBJID': subject.usubjid,
                'MHSEQ': mhseq,
                'MHTERM': condition.get('term', 'UNKNOWN CONDITION'),
                'MHDECOD': condition.get('term', 'UNKNOWN CONDITION').upper(),  # Standardized term
                'MHCAT': condition.get('category', 'GENERAL'),
                'MHBODSYS': condition.get('bodsys', ''),  # Body system/organ class
                'MHSTDTC': format_iso_date(start_date),
                'MHENDTC': format_iso_date(end_date) if end_date else '',
                'MHENRF': mhenrf,
                'EPOCH': 'SCREENING',
            }
            
            # Derive study days
            if rfstdtc:
                record['MHSTDY'] = derive_study_day(start_date, rfstdtc)
                if end_date:
                    record['MHENDY'] = derive_study_day(end_date, rfstdtc)
                else:
                    record['MHENDY'] = ''
            else:
                record['MHSTDY'] = ''
                record['MHENDY'] = ''
            
            records.append(record)
        
        return records
    
    def _empty_mh(self) -> pd.DataFrame:
        """Return empty MH DataFrame with correct columns."""
        return pd.DataFrame(columns=[
            'STUDYID', 'DOMAIN', 'USUBJID', 'MHSEQ', 'MHTERM', 'MHDECOD', 'MHCAT', 'MHBODSYS',
            'MHSTDTC', 'MHENDTC', 'MHENRF', 'MHSTDY', 'MHENDY', 'EPOCH'
        ])
