"""
SDTM Synthetic Data Generator - Laboratory Generator

This module generates the Laboratory (LB) dataset.
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


# Default laboratory tests
DEFAULT_LB_TESTS = [
    # Chemistry
    {'testcd': 'ALT', 'test': 'Alanine Aminotransferase', 'cat': 'CHEMISTRY', 'unit': 'U/L',
     'mean': 25, 'sd': 10, 'low': 5, 'high': 200, 'lln': 7, 'uln': 56},
    {'testcd': 'AST', 'test': 'Aspartate Aminotransferase', 'cat': 'CHEMISTRY', 'unit': 'U/L',
     'mean': 22, 'sd': 8, 'low': 5, 'high': 200, 'lln': 10, 'uln': 40},
    {'testcd': 'BILI', 'test': 'Bilirubin', 'cat': 'CHEMISTRY', 'unit': 'mg/dL',
     'mean': 0.7, 'sd': 0.3, 'low': 0.1, 'high': 5.0, 'lln': 0.1, 'uln': 1.2},
    {'testcd': 'CREAT', 'test': 'Creatinine', 'cat': 'CHEMISTRY', 'unit': 'mg/dL',
     'mean': 0.95, 'sd': 0.2, 'low': 0.3, 'high': 5.0, 'lln': 0.7, 'uln': 1.3},
    {'testcd': 'GLUC', 'test': 'Glucose', 'cat': 'CHEMISTRY', 'unit': 'mg/dL',
     'mean': 95, 'sd': 15, 'low': 50, 'high': 400, 'lln': 70, 'uln': 100},
    {'testcd': 'SODIUM', 'test': 'Sodium', 'cat': 'CHEMISTRY', 'unit': 'mmol/L',
     'mean': 140, 'sd': 3, 'low': 125, 'high': 155, 'lln': 136, 'uln': 145},
    {'testcd': 'POTASS', 'test': 'Potassium', 'cat': 'CHEMISTRY', 'unit': 'mmol/L',
     'mean': 4.2, 'sd': 0.4, 'low': 2.5, 'high': 6.5, 'lln': 3.5, 'uln': 5.0},
    # Hematology
    {'testcd': 'HGB', 'test': 'Hemoglobin', 'cat': 'HEMATOLOGY', 'unit': 'g/dL',
     'mean': 14.0, 'sd': 1.5, 'low': 8, 'high': 20, 'lln': 12.0, 'uln': 16.0},
    {'testcd': 'HCT', 'test': 'Hematocrit', 'cat': 'HEMATOLOGY', 'unit': '%',
     'mean': 42, 'sd': 4, 'low': 25, 'high': 55, 'lln': 36, 'uln': 48},
    {'testcd': 'WBC', 'test': 'White Blood Cell Count', 'cat': 'HEMATOLOGY', 'unit': '10^9/L',
     'mean': 7.0, 'sd': 2.0, 'low': 2.0, 'high': 20.0, 'lln': 4.0, 'uln': 11.0},
    {'testcd': 'PLAT', 'test': 'Platelet Count', 'cat': 'HEMATOLOGY', 'unit': '10^9/L',
     'mean': 250, 'sd': 60, 'low': 50, 'high': 600, 'lln': 150, 'uln': 400},
]


class LaboratoryGenerator:
    """
    Generates the Laboratory (LB) dataset.
    
    Records laboratory test results at scheduled visits.
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
        
        # Use LB tests from spec if available
        if spec.lb_model and spec.lb_model.tests:
            self.lb_tests = [self._test_spec_to_dict(t) for t in spec.lb_model.tests]
        else:
            self.lb_tests = DEFAULT_LB_TESTS
    
    def _test_spec_to_dict(self, test: ValueModelItem) -> Dict[str, Any]:
        """Convert ValueModelItem to dictionary format."""
        # Derive category from test name
        cat = 'CHEMISTRY'
        if test.testcd in ['HGB', 'HCT', 'WBC', 'PLAT', 'RBC']:
            cat = 'HEMATOLOGY'
        elif test.testcd in ['URATE', 'UPROT']:
            cat = 'URINALYSIS'
        
        # Estimate LLN/ULN from plausible ranges
        lln = test.plausible_min * 1.5 if test.plausible_min else None
        uln = test.plausible_max * 0.7 if test.plausible_max else None
        
        return {
            'testcd': test.testcd,
            'test': test.test,
            'cat': cat,
            'unit': test.unit,
            'mean': test.baseline_mean,
            'sd': test.baseline_sd,
            'low': test.plausible_min,
            'high': test.plausible_max,
            'lln': lln,
            'uln': uln,
        }
    
    def generate(self) -> pd.DataFrame:
        """
        Generate LB dataset.
        
        Includes SD0057 fix: LBORNRLO, LBORNRHI, LBLOBXFL expected variables.
        
        Returns:
            LB DataFrame
        """
        records = []
        
        for subject in self.registry.get_enrolled_subjects():
            subject_records = self._generate_subject_lb(subject)
            records.extend(subject_records)
        
        if not records:
            return self._empty_lb()
        
        df = pd.DataFrame(records)
        
        # Sort by USUBJID, VISITNUM, LBCAT, LBTESTCD
        df = df.sort_values(['USUBJID', 'VISITNUM', 'LBCAT', 'LBTESTCD']).reset_index(drop=True)
        
        # SD0057 FIX: Derive LBLOBXFL (last observation before exposure flag)
        # This is the baseline flag - Y for the last measurement before first dose
        df = self._derive_baseline_flags(df)
        
        cols = ['STUDYID', 'DOMAIN', 'USUBJID', 'LBSEQ', 'LBTESTCD', 'LBTEST', 'LBCAT',
                'LBORRES', 'LBORRESU', 'LBORNRLO', 'LBORNRHI',  # SD0057: original ranges
                'LBSTRESC', 'LBSTRESN', 'LBSTRESU', 'LBSTNRLO', 'LBSTNRHI', 
                'LBRESSCL',  # Result scale classification (QUANTITATIVE/ORDINAL/NOMINAL)
                'LBNRIND',
                'LBBLFL', 'LBLOBXFL',  # SD0057: baseline flags
                'LBDTC', 'LBDY', 'VISITNUM', 'VISIT', 'EPOCH']
        
        return df[[c for c in cols if c in df.columns]]
    
    def _derive_baseline_flags(self, df: pd.DataFrame) -> pd.DataFrame:
        """Derive LBBLFL and LBLOBXFL baseline flags.
        
        LBBLFL = Y for the baseline record (typically screening/day 1)
        LBLOBXFL = Y for last observation before first exposure
        """
        df = df.copy()
        df['LBBLFL'] = ''
        df['LBLOBXFL'] = ''
        
        for usubjid in df['USUBJID'].unique():
            subject = self.registry.get_subject(usubjid)
            if not subject or not subject.rfstdtc:
                continue
            
            rfstdtc = parse_date(subject.rfstdtc)
            subj_mask = df['USUBJID'] == usubjid
            subj_df = df[subj_mask]
            
            for testcd in subj_df['LBTESTCD'].unique():
                test_mask = subj_mask & (df['LBTESTCD'] == testcd)
                test_df = df[test_mask]
                
                # Find records on or before first dose
                baseline_candidates = []
                for idx in test_df.index:
                    lbdtc = test_df.loc[idx, 'LBDTC']
                    if lbdtc:
                        try:
                            lb_date = parse_date(lbdtc)
                            if lb_date <= rfstdtc:
                                baseline_candidates.append((idx, lb_date))
                        except:
                            pass
                
                # Set LBLOBXFL = Y for the last one before/on first dose
                if baseline_candidates:
                    # Sort by date descending, get last (closest to first dose)
                    baseline_candidates.sort(key=lambda x: x[1], reverse=True)
                    last_baseline_idx = baseline_candidates[0][0]
                    df.loc[last_baseline_idx, 'LBLOBXFL'] = 'Y'
                    df.loc[last_baseline_idx, 'LBBLFL'] = 'Y'
        
        return df
    
    def _generate_subject_lb(self, subject: SubjectInfo) -> List[Dict[str, Any]]:
        """Generate LB records for a single subject."""
        records = []
        
        # Get timeline
        timeline = self.timeline_engine.get_subject_timeline(subject.usubjid)
        if timeline is None:
            return records
        
        rfstdtc = parse_date(subject.rfstdtc) if subject.rfstdtc else None
        
        # Generate subject-specific baseline values
        subject_baselines = self._generate_subject_baselines()
        
        # Generate LB at each visit
        for visit in self.spec.visits:
            # Check if visit has LB collection
            if not visit.collection_flags.lb:
                continue
            
            visit_date = timeline.visit_dates.get(visit.visitnum)
            if visit_date is None:
                continue
            
            epoch = timeline.get_epoch_for_date(visit_date) or visit.epoch
            
            for test in self.lb_tests:
                lbseq = self.seq_tracker.get_next_seq('LB', subject.usubjid)
                
                # Generate value with variation from baseline
                baseline = subject_baselines.get(test['testcd'], test['mean'])
                value = self._generate_value_with_variation(test, baseline, visit.visitnum)
                
                # Round appropriately based on test
                if test['testcd'] in ['BILI', 'CREAT']:
                    value = round(value, 2)
                elif test['testcd'] in ['POTASS', 'SODIUM']:
                    value = round(value, 1)
                else:
                    value = round(value, 1)
                
                # Determine normal range indicator (LBNRIND)
                # LBNRIND contains the interpretation: NORMAL, LOW, HIGH
                lln = test.get('lln')
                uln = test.get('uln')
                if lln is not None and value < lln:
                    lbnrind = 'LOW'
                elif uln is not None and value > uln:
                    lbnrind = 'HIGH'
                else:
                    lbnrind = 'NORMAL'
                
                # SDTM LB Model for QUANTITATIVE tests:
                # - LBORRES/LBORRESU: Original result and units
                # - LBSTRESN: Numeric standardized result
                # - LBSTRESC: Character copy of LBSTRESN (REQUIRED when test is done)
                # - LBRESSCL: Result scale classification (QUANTITATIVE for numeric tests)
                # - LBNRIND: Interpretation (NORMAL/HIGH/LOW)
                #
                # Format LBSTRESC: use integer format if whole number, otherwise decimal
                if value == int(value):
                    lbstresc = str(int(value))  # "398" not "398.0"
                else:
                    lbstresc = str(value)       # "43.9"
                
                record = {
                    'STUDYID': self.spec.study_id,
                    'DOMAIN': 'LB',
                    'USUBJID': subject.usubjid,
                    'LBSEQ': lbseq,
                    'LBTESTCD': test['testcd'],
                    'LBTEST': test['test'],
                    'LBCAT': test['cat'],
                    'LBORRES': lbstresc,             # Original result (same as standardized for our tests)
                    'LBORRESU': test['unit'],        # Original units
                    'LBORNRLO': str(lln) if lln else '',
                    'LBORNRHI': str(uln) if uln else '',
                    'LBSTRESC': lbstresc,            # Character standardized result (REQUIRED)
                    'LBSTRESN': value,               # Numeric standardized result
                    'LBSTRESU': test['unit'],
                    'LBSTNRLO': lln if lln else '',
                    'LBSTNRHI': uln if uln else '',
                    'LBRESSCL': 'QUANTITATIVE',      # Result scale - explains numeric result
                    'LBNRIND': lbnrind,              # Interpretation: NORMAL/HIGH/LOW
                    'LBDTC': format_iso_date(visit_date),
                    'VISITNUM': visit.visitnum,
                    'VISIT': visit.visit,
                    'EPOCH': epoch,
                }
                
                # Derive study day
                if rfstdtc:
                    record['LBDY'] = derive_study_day(visit_date, rfstdtc)
                else:
                    record['LBDY'] = ''
                
                records.append(record)
        
        return records
    
    def _generate_subject_baselines(self) -> Dict[str, float]:
        """Generate subject-specific baseline values."""
        baselines = {}
        for test in self.lb_tests:
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
        variation_sd = test['sd'] * 0.25  # 25% of between-subject SD
        
        value = self.rng.truncated_normal(
            mean=baseline,
            std=variation_sd,
            low=test['low'],
            high=test['high']
        )
        
        return value
    
    def _empty_lb(self) -> pd.DataFrame:
        """Return empty LB DataFrame with correct columns."""
        return pd.DataFrame(columns=[
            'STUDYID', 'DOMAIN', 'USUBJID', 'LBSEQ', 'LBTESTCD', 'LBTEST', 'LBCAT',
            'LBORRES', 'LBORRESU', 'LBSTRESC', 'LBSTRESN', 'LBSTRESU',
            'LBSTNRLO', 'LBSTNRHI', 'LBNRIND',
            'LBDTC', 'LBDY', 'VISITNUM', 'VISIT', 'EPOCH'
        ])
