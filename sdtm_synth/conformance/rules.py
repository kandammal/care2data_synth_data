"""
SDTM Synthetic Data Generator - Conformance Rules

This module defines validation rules for SDTM conformance.
"""

from __future__ import annotations
from typing import List, Dict, Any, Optional, Callable
from dataclasses import dataclass
from enum import Enum
import pandas as pd


class RuleSeverity(Enum):
    """Severity levels for validation rules."""
    ERROR = "ERROR"
    WARNING = "WARNING"
    INFO = "INFO"


@dataclass
class ValidationResult:
    """Result of a validation check."""
    rule_id: str
    rule_name: str
    severity: RuleSeverity
    passed: bool
    message: str
    affected_records: List[str] = None  # List of USUBJIDs or record identifiers
    
    def __post_init__(self):
        if self.affected_records is None:
            self.affected_records = []


@dataclass
class ConformanceRule:
    """Definition of a conformance rule."""
    rule_id: str
    rule_name: str
    description: str
    severity: RuleSeverity
    domains: List[str]  # Domains this rule applies to
    check_function: Callable[[pd.DataFrame, Dict[str, pd.DataFrame]], ValidationResult]


def check_required_variables(df: pd.DataFrame, domain: str, required_vars: List[str]) -> ValidationResult:
    """Check that required variables are present."""
    missing = [v for v in required_vars if v not in df.columns]
    
    if missing:
        return ValidationResult(
            rule_id="REQ_VARS",
            rule_name="Required Variables Present",
            severity=RuleSeverity.ERROR,
            passed=False,
            message=f"Domain {domain} missing required variables: {missing}"
        )
    
    return ValidationResult(
        rule_id="REQ_VARS",
        rule_name="Required Variables Present",
        severity=RuleSeverity.ERROR,
        passed=True,
        message=f"Domain {domain} has all required variables"
    )


def check_unique_keys(df: pd.DataFrame, domain: str, key_vars: List[str]) -> ValidationResult:
    """Check that key variables form unique records."""
    if df.empty:
        return ValidationResult(
            rule_id="UNIQUE_KEY",
            rule_name="Unique Record Keys",
            severity=RuleSeverity.ERROR,
            passed=True,
            message=f"Domain {domain} is empty"
        )
    
    # Check for duplicates
    duplicates = df[df.duplicated(subset=key_vars, keep=False)]
    
    if not duplicates.empty:
        affected = duplicates['USUBJID'].unique().tolist() if 'USUBJID' in duplicates.columns else []
        return ValidationResult(
            rule_id="UNIQUE_KEY",
            rule_name="Unique Record Keys",
            severity=RuleSeverity.ERROR,
            passed=False,
            message=f"Domain {domain} has {len(duplicates)} duplicate records on key {key_vars}",
            affected_records=affected
        )
    
    return ValidationResult(
        rule_id="UNIQUE_KEY",
        rule_name="Unique Record Keys",
        severity=RuleSeverity.ERROR,
        passed=True,
        message=f"Domain {domain} has unique records on key {key_vars}"
    )


def check_valid_dates(df: pd.DataFrame, domain: str, date_vars: List[str]) -> ValidationResult:
    """Check that date variables are in valid ISO 8601 format."""
    import re
    
    iso_pattern = re.compile(r'^\d{4}(-\d{2})?(-\d{2})?(T\d{2}:\d{2}:\d{2})?$')
    invalid_dates = []
    
    for var in date_vars:
        if var in df.columns:
            for idx, val in df[var].items():
                if pd.notna(val) and val != '' and not iso_pattern.match(str(val)):
                    if 'USUBJID' in df.columns:
                        invalid_dates.append(f"{df.loc[idx, 'USUBJID']}/{var}={val}")
                    else:
                        invalid_dates.append(f"row {idx}/{var}={val}")
    
    if invalid_dates:
        return ValidationResult(
            rule_id="VALID_DATES",
            rule_name="Valid ISO 8601 Dates",
            severity=RuleSeverity.ERROR,
            passed=False,
            message=f"Domain {domain} has {len(invalid_dates)} invalid dates: {invalid_dates[:5]}..."
        )
    
    return ValidationResult(
        rule_id="VALID_DATES",
        rule_name="Valid ISO 8601 Dates",
        severity=RuleSeverity.ERROR,
        passed=True,
        message=f"Domain {domain} has valid dates"
    )


def check_seq_positive(df: pd.DataFrame, domain: str) -> ValidationResult:
    """Check that --SEQ is positive integer."""
    seq_var = f"{domain}SEQ"
    
    if seq_var not in df.columns:
        return ValidationResult(
            rule_id="SEQ_POSITIVE",
            rule_name="Sequence Positive Integer",
            severity=RuleSeverity.WARNING,
            passed=True,
            message=f"Domain {domain} does not have {seq_var} variable"
        )
    
    if df.empty:
        return ValidationResult(
            rule_id="SEQ_POSITIVE",
            rule_name="Sequence Positive Integer",
            severity=RuleSeverity.ERROR,
            passed=True,
            message=f"Domain {domain} is empty"
        )
    
    invalid = df[df[seq_var] <= 0]
    
    if not invalid.empty:
        affected = invalid['USUBJID'].unique().tolist() if 'USUBJID' in invalid.columns else []
        return ValidationResult(
            rule_id="SEQ_POSITIVE",
            rule_name="Sequence Positive Integer",
            severity=RuleSeverity.ERROR,
            passed=False,
            message=f"Domain {domain} has {len(invalid)} records with non-positive {seq_var}",
            affected_records=affected
        )
    
    return ValidationResult(
        rule_id="SEQ_POSITIVE",
        rule_name="Sequence Positive Integer",
        severity=RuleSeverity.ERROR,
        passed=True,
        message=f"Domain {domain} has all positive {seq_var} values"
    )


def check_interval_validity(df: pd.DataFrame, domain: str, start_var: str, end_var: str) -> ValidationResult:
    """Check that start date <= end date for intervals."""
    from ..utils.dates import parse_iso_date
    
    if start_var not in df.columns or end_var not in df.columns:
        return ValidationResult(
            rule_id="INTERVAL_VALID",
            rule_name="Valid Interval (Start <= End)",
            severity=RuleSeverity.WARNING,
            passed=True,
            message=f"Domain {domain} does not have {start_var} and {end_var}"
        )
    
    invalid_intervals = []
    
    for idx, row in df.iterrows():
        start_str = row.get(start_var, '')
        end_str = row.get(end_var, '')
        
        if pd.notna(start_str) and pd.notna(end_str) and start_str != '' and end_str != '':
            start = parse_iso_date(str(start_str))
            end = parse_iso_date(str(end_str))
            
            if start and end and start > end:
                usubjid = row.get('USUBJID', f'row {idx}')
                invalid_intervals.append(usubjid)
    
    if invalid_intervals:
        return ValidationResult(
            rule_id="INTERVAL_VALID",
            rule_name="Valid Interval (Start <= End)",
            severity=RuleSeverity.ERROR,
            passed=False,
            message=f"Domain {domain} has {len(invalid_intervals)} records where {start_var} > {end_var}",
            affected_records=invalid_intervals[:10]
        )
    
    return ValidationResult(
        rule_id="INTERVAL_VALID",
        rule_name="Valid Interval (Start <= End)",
        severity=RuleSeverity.ERROR,
        passed=True,
        message=f"Domain {domain} has valid intervals"
    )


def check_se_gapless(se_df: pd.DataFrame, all_datasets: Dict[str, pd.DataFrame]) -> ValidationResult:
    """Check that SE elements are gapless (SEENDTC[i] = SESTDTC[i+1])."""
    if se_df.empty:
        return ValidationResult(
            rule_id="SE_GAPLESS",
            rule_name="SE Gapless Elements",
            severity=RuleSeverity.ERROR,
            passed=True,
            message="SE is empty"
        )
    
    gaps = []
    
    for usubjid in se_df['USUBJID'].unique():
        subj_se = se_df[se_df['USUBJID'] == usubjid].sort_values('SESEQ')
        
        if len(subj_se) < 2:
            continue
        
        for i in range(len(subj_se) - 1):
            current_end = subj_se.iloc[i]['SEENDTC']
            next_start = subj_se.iloc[i + 1]['SESTDTC']
            
            if pd.notna(current_end) and pd.notna(next_start):
                if str(current_end) != str(next_start):
                    gaps.append(usubjid)
                    break
    
    if gaps:
        return ValidationResult(
            rule_id="SE_GAPLESS",
            rule_name="SE Gapless Elements",
            severity=RuleSeverity.WARNING,
            passed=False,
            message=f"SE has gaps between elements for {len(gaps)} subjects",
            affected_records=gaps[:10]
        )
    
    return ValidationResult(
        rule_id="SE_GAPLESS",
        rule_name="SE Gapless Elements",
        severity=RuleSeverity.WARNING,
        passed=True,
        message="SE elements are gapless"
    )


def check_dm_arm_consistency(dm_df: pd.DataFrame, all_datasets: Dict[str, pd.DataFrame]) -> ValidationResult:
    """Check that DM.ARMCD/ARM is consistent with DM.ACTARMCD/ACTARM."""
    if dm_df.empty:
        return ValidationResult(
            rule_id="DM_ARM_CONSISTENT",
            rule_name="DM ARM Consistency",
            severity=RuleSeverity.WARNING,
            passed=True,
            message="DM is empty"
        )
    
    inconsistent = []
    
    for idx, row in dm_df.iterrows():
        # Screen failures should have SCRNFAIL/SCREEN FAILURE for ARMCD/ARM
        # but empty ACTARMCD/ACTARM
        if row.get('ARMCD') == 'SCRNFAIL':
            if row.get('ACTARMCD') not in ['', None]:
                inconsistent.append(row.get('USUBJID', f'row {idx}'))
        else:
            # Non-screen-failures should have matching ARM codes
            if row.get('ARMCD') != row.get('ACTARMCD') or row.get('ARM') != row.get('ACTARM'):
                inconsistent.append(row.get('USUBJID', f'row {idx}'))
    
    if inconsistent:
        return ValidationResult(
            rule_id="DM_ARM_CONSISTENT",
            rule_name="DM ARM Consistency",
            severity=RuleSeverity.WARNING,
            passed=False,
            message=f"DM has {len(inconsistent)} records with inconsistent ARM values",
            affected_records=inconsistent[:10]
        )
    
    return ValidationResult(
        rule_id="DM_ARM_CONSISTENT",
        rule_name="DM ARM Consistency",
        severity=RuleSeverity.WARNING,
        passed=True,
        message="DM ARM values are consistent"
    )


# Domain-specific required variables
REQUIRED_VARIABLES = {
    'DM': ['STUDYID', 'DOMAIN', 'USUBJID', 'SUBJID', 'AGE', 'AGEU', 'SEX', 'ARMCD', 'ARM'],
    'TE': ['STUDYID', 'DOMAIN', 'ETCD', 'ELEMENT'],
    'TA': ['STUDYID', 'DOMAIN', 'ARMCD', 'ARM', 'TAETORD', 'ETCD', 'ELEMENT'],
    'TS': ['STUDYID', 'DOMAIN', 'TSSEQ', 'TSPARMCD', 'TSVAL'],
    'TV': ['STUDYID', 'DOMAIN', 'VISITNUM', 'VISIT'],
    'SE': ['STUDYID', 'DOMAIN', 'USUBJID', 'SESEQ', 'ETCD', 'SESTDTC'],
    'SV': ['STUDYID', 'DOMAIN', 'USUBJID', 'VISITNUM', 'VISIT'],
    'DS': ['STUDYID', 'DOMAIN', 'USUBJID', 'DSSEQ', 'DSTERM', 'DSDECOD'],
    'MH': ['STUDYID', 'DOMAIN', 'USUBJID', 'MHSEQ', 'MHTERM'],
    'EX': ['STUDYID', 'DOMAIN', 'USUBJID', 'EXSEQ', 'EXTRT', 'EXSTDTC'],
    'CM': ['STUDYID', 'DOMAIN', 'USUBJID', 'CMSEQ', 'CMTRT'],
    'VS': ['STUDYID', 'DOMAIN', 'USUBJID', 'VSSEQ', 'VSTESTCD', 'VSTEST'],
    'LB': ['STUDYID', 'DOMAIN', 'USUBJID', 'LBSEQ', 'LBTESTCD', 'LBTEST'],
    'AE': ['STUDYID', 'DOMAIN', 'USUBJID', 'AESEQ', 'AETERM'],
}

# Domain-specific key variables
KEY_VARIABLES = {
    'DM': ['STUDYID', 'USUBJID'],
    'TE': ['STUDYID', 'ETCD'],
    'TA': ['STUDYID', 'ARMCD', 'TAETORD'],
    'TS': ['STUDYID', 'TSSEQ'],
    'TV': ['STUDYID', 'VISITNUM'],
    'SE': ['STUDYID', 'USUBJID', 'SESEQ'],
    'SV': ['STUDYID', 'USUBJID', 'VISITNUM'],
    'DS': ['STUDYID', 'USUBJID', 'DSSEQ'],
    'MH': ['STUDYID', 'USUBJID', 'MHSEQ'],
    'EX': ['STUDYID', 'USUBJID', 'EXSEQ'],
    'CM': ['STUDYID', 'USUBJID', 'CMSEQ'],
    'VS': ['STUDYID', 'USUBJID', 'VSSEQ'],
    'LB': ['STUDYID', 'USUBJID', 'LBSEQ'],
    'AE': ['STUDYID', 'USUBJID', 'AESEQ'],
}

# Domain-specific date variables
DATE_VARIABLES = {
    'DM': ['RFSTDTC', 'RFENDTC', 'RFXSTDTC', 'RFXENDTC', 'RFICDTC', 'RFPENDTC'],
    'SE': ['SESTDTC', 'SEENDTC'],
    'SV': ['SVSTDTC', 'SVENDTC'],
    'DS': ['DSSTDTC', 'DSDTC'],
    'MH': ['MHSTDTC', 'MHENDTC'],
    'EX': ['EXSTDTC', 'EXENDTC'],
    'CM': ['CMSTDTC', 'CMENDTC'],
    'VS': ['VSDTC'],
    'LB': ['LBDTC'],
    'AE': ['AESTDTC', 'AEENDTC'],
}
