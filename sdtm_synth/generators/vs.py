"""
SDTM Synthetic Data Generator - Vital Signs Generator

This module generates the Vital Signs (VS) dataset.
"""

from __future__ import annotations
from typing import List, Dict, Any, Optional
from datetime import date
import pandas as pd

from ..spec.models import TrialDesignSpec, ValueModelItem
from ..backbone.subjects import SubjectRegistry, SubjectInfo
from ..timeline.engine import TimelineEngine, SubjectTimeline
from ..utils.rng import get_rng
from ..utils.dates import format_iso_date, parse_date, derive_study_day
from ..utils.ids import SequenceTracker


# Default vital signs tests - using CDISC CT VSRESU codelist values
# VSRESU codelist: beats/min (pulse), breaths/min (resp), C (temp), mmHg (BP), cm, kg, kg/m2
DEFAULT_VS_TESTS = [
    {'testcd': 'SYSBP', 'test': 'Systolic Blood Pressure', 'unit': 'mmHg',
     'mean': 120, 'sd': 12, 'low': 90, 'high': 180},
    {'testcd': 'DIABP', 'test': 'Diastolic Blood Pressure', 'unit': 'mmHg',
     'mean': 75, 'sd': 8, 'low': 50, 'high': 110},
    {'testcd': 'PULSE', 'test': 'Pulse Rate', 'unit': 'beats/min',  # VSRESU C49673
     'mean': 72, 'sd': 10, 'low': 50, 'high': 120},
    {'testcd': 'TEMP', 'test': 'Temperature', 'unit': 'C',          # VSRESU C42559
     'mean': 36.8, 'sd': 0.4, 'low': 35.0, 'high': 39.0},
    {'testcd': 'RESP', 'test': 'Respiratory Rate', 'unit': 'breaths/min',  # VSRESU C49674
     'mean': 16, 'sd': 3, 'low': 10, 'high': 30},
    {'testcd': 'WEIGHT', 'test': 'Weight', 'unit': 'kg',
     'mean': 75, 'sd': 15, 'low': 40, 'high': 150},
    {'testcd': 'HEIGHT', 'test': 'Height', 'unit': 'cm',
     'mean': 170, 'sd': 10, 'low': 140, 'high': 200},
]


class VitalSignsGenerator:
    """
    Generates the Vital Signs (VS) dataset.
    
    Records vital sign measurements at scheduled visits.
    """
    
    def __init__(self, 
                 spec: TrialDesignSpec, 
                 registry: SubjectRegistry,
                 timeline_engine: TimelineEngine):
        """
        Initialize the generator.
        
        Args:
            spec: Trial design specification
            registry: Subject registry
            timeline_engine: Timeline engine with subject timelines
        """
        self.spec = spec
        self.registry = registry
        self.timeline_engine = timeline_engine
        self.rng = get_rng()
        self.seq_tracker = SequenceTracker()
        
        # Use VS tests from spec if available
        if spec.vs_model and spec.vs_model.tests:
            self.vs_tests = [self._test_spec_to_dict(t) for t in spec.vs_model.tests]
        else:
            self.vs_tests = DEFAULT_VS_TESTS
    
    def _test_spec_to_dict(self, test: ValueModelItem) -> Dict[str, Any]:
        """Convert ValueModelItem to dictionary format."""
        return {
            'testcd': test.testcd,
            'test': test.test,
            'unit': test.unit,
            'mean': test.baseline_mean,
            'sd': test.baseline_sd,
            'low': test.plausible_min,
            'high': test.plausible_max,
        }
    
    def generate(self) -> pd.DataFrame:
        """
        Generate VS dataset.
        
        Includes SD0057 fix: VSLOBXFL expected variable.
        
        Returns:
            VS DataFrame
        """
        records = []
        
        for subject in self.registry.get_enrolled_subjects():
            subject_records = self._generate_subject_vs(subject)
            records.extend(subject_records)
        
        if not records:
            return self._empty_vs()
        
        df = pd.DataFrame(records)
        
        # Sort by USUBJID, VISITNUM, VSTESTCD
        df = df.sort_values(['USUBJID', 'VISITNUM', 'VSTESTCD']).reset_index(drop=True)
        
        # SD0057 FIX: Derive VSLOBXFL (last observation before exposure flag)
        df = self._derive_baseline_flags(df)
        
        cols = ['STUDYID', 'DOMAIN', 'USUBJID', 'VSSEQ', 'VSTESTCD', 'VSTEST',
                'VSORRES', 'VSORRESU', 'VSSTRESC', 'VSSTRESN', 'VSSTRESU',
                'VSBLFL', 'VSLOBXFL',  # SD0057: baseline flags
                'VSDTC', 'VSDY', 'VISITNUM', 'VISIT', 'EPOCH']
        
        return df[[c for c in cols if c in df.columns]]
    
    def _derive_baseline_flags(self, df: pd.DataFrame) -> pd.DataFrame:
        """Derive VSBLFL and VSLOBXFL baseline flags.
        
        VSBLFL = Y for the baseline record (typically screening/day 1)
        VSLOBXFL = Y for last observation before first exposure
        """
        df = df.copy()
        df['VSBLFL'] = ''
        df['VSLOBXFL'] = ''
        
        for usubjid in df['USUBJID'].unique():
            subject = self.registry.get_subject(usubjid)
            if not subject or not subject.rfstdtc:
                continue
            
            rfstdtc = parse_date(subject.rfstdtc)
            subj_mask = df['USUBJID'] == usubjid
            subj_df = df[subj_mask]
            
            for testcd in subj_df['VSTESTCD'].unique():
                test_mask = subj_mask & (df['VSTESTCD'] == testcd)
                test_df = df[test_mask]
                
                # Find records on or before first dose
                baseline_candidates = []
                for idx in test_df.index:
                    vsdtc = test_df.loc[idx, 'VSDTC']
                    if vsdtc:
                        try:
                            vs_date = parse_date(vsdtc)
                            if vs_date <= rfstdtc:
                                baseline_candidates.append((idx, vs_date))
                        except:
                            pass
                
                # Set VSLOBXFL = Y for the last one before/on first dose
                if baseline_candidates:
                    baseline_candidates.sort(key=lambda x: x[1], reverse=True)
                    last_baseline_idx = baseline_candidates[0][0]
                    df.loc[last_baseline_idx, 'VSLOBXFL'] = 'Y'
                    df.loc[last_baseline_idx, 'VSBLFL'] = 'Y'
        
        return df
    
    def _generate_subject_vs(self, subject: SubjectInfo) -> List[Dict[str, Any]]:
        """Generate VS records for a single subject."""
        records = []
        
        # Get timeline
        timeline = self.timeline_engine.get_subject_timeline(subject.usubjid)
        if timeline is None:
            return records
        
        rfstdtc = parse_date(subject.rfstdtc) if subject.rfstdtc else None
        
        # Generate subject-specific baseline values
        subject_baselines = self._generate_subject_baselines()
        
        # Generate VS at each visit
        for visit in self.spec.visits:
            # Check if visit has VS collection
            if not visit.collection_flags.vs:
                continue
            
            visit_date = timeline.visit_dates.get(visit.visitnum)
            if visit_date is None:
                continue
            
            epoch = timeline.get_epoch_for_date(visit_date) or visit.epoch
            
            for test in self.vs_tests:
                vsseq = self.seq_tracker.get_next_seq('VS', subject.usubjid)
                
                # Generate value with variation from baseline
                baseline = subject_baselines.get(test['testcd'], test['mean'])
                value = self._generate_value_with_variation(test, baseline, visit.visitnum)
                
                # Round appropriately
                if test['testcd'] == 'TEMP':
                    value = round(value, 1)
                elif test['testcd'] in ['HEIGHT', 'WEIGHT']:
                    value = round(value, 1)
                else:
                    value = round(value)
                
                record = {
                    'STUDYID': self.spec.study_id,
                    'DOMAIN': 'VS',
                    'USUBJID': subject.usubjid,
                    'VSSEQ': vsseq,
                    'VSTESTCD': test['testcd'],
                    'VSTEST': test['test'],
                    'VSORRES': str(value),
                    'VSORRESU': test['unit'],
                    'VSSTRESC': str(value),
                    'VSSTRESN': value,
                    'VSSTRESU': test['unit'],
                    'VSDTC': format_iso_date(visit_date),
                    'VISITNUM': visit.visitnum,
                    'VISIT': visit.visit,
                    'EPOCH': epoch,
                }
                
                # Derive study day
                if rfstdtc:
                    record['VSDY'] = derive_study_day(visit_date, rfstdtc)
                else:
                    record['VSDY'] = ''
                
                records.append(record)
        
        return records
    
    def _generate_subject_baselines(self) -> Dict[str, float]:
        """Generate subject-specific baseline values."""
        baselines = {}
        for test in self.vs_tests:
            baseline = self.rng.truncated_normal(
                mean=test['mean'],
                std=test['sd'],
                low=test['low'],
                high=test['high']
            )
            baselines[test['testcd']] = baseline
        return baselines
    
    def _generate_value_with_variation(
        self, 
        test: Dict[str, Any], 
        baseline: float, 
        visitnum: int
    ) -> float:
        """Generate value with visit-to-visit variation from baseline."""
        # Add small random variation (within-subject variability)
        variation_sd = test['sd'] * 0.3  # 30% of between-subject SD
        
        value = self.rng.truncated_normal(
            mean=baseline,
            std=variation_sd,
            low=test['low'],
            high=test['high']
        )
        
        return value
    
    def _empty_vs(self) -> pd.DataFrame:
        """Return empty VS DataFrame with correct columns."""
        return pd.DataFrame(columns=[
            'STUDYID', 'DOMAIN', 'USUBJID', 'VSSEQ', 'VSTESTCD', 'VSTEST',
            'VSORRES', 'VSORRESU', 'VSSTRESC', 'VSSTRESN', 'VSSTRESU',
            'VSDTC', 'VSDY', 'VISITNUM', 'VISIT', 'EPOCH'
        ])
