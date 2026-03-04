"""
SDTM Conformance Repair Layer

Applies idempotent post-generation repairs: sorting, study day derivation,
epoch assignment, and cross-domain field repair (DM.RFXENDTC from EX, etc.).

This is the REPAIR path. For tagged-category validation, see v2_validator.py.
"""

from __future__ import annotations
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass, field
import pandas as pd

from .rules import (
    ValidationResult, RuleSeverity,
    check_required_variables, check_unique_keys, check_valid_dates,
    check_seq_positive, check_interval_validity,
    check_se_gapless, check_dm_arm_consistency,
    REQUIRED_VARIABLES, KEY_VARIABLES, DATE_VARIABLES
)


@dataclass
class ConformanceReport:
    """Report summarizing conformance validation results."""
    total_rules: int = 0
    passed: int = 0
    failed: int = 0
    warnings: int = 0
    errors: int = 0
    results: List[ValidationResult] = field(default_factory=list)
    
    def add_result(self, result: ValidationResult) -> None:
        """Add a validation result to the report."""
        self.results.append(result)
        self.total_rules += 1
        
        if result.passed:
            self.passed += 1
        else:
            self.failed += 1
            if result.severity == RuleSeverity.ERROR:
                self.errors += 1
            elif result.severity == RuleSeverity.WARNING:
                self.warnings += 1
    
    def to_dataframe(self) -> pd.DataFrame:
        """Convert report to DataFrame."""
        records = []
        for r in self.results:
            records.append({
                'Rule ID': r.rule_id,
                'Rule Name': r.rule_name,
                'Severity': r.severity.value,
                'Passed': r.passed,
                'Message': r.message,
                'Affected Records': len(r.affected_records) if r.affected_records else 0,
            })
        return pd.DataFrame(records)
    
    def summary(self) -> str:
        """Generate summary string."""
        return (
            f"Conformance Report: {self.passed}/{self.total_rules} rules passed\n"
            f"  Errors: {self.errors}, Warnings: {self.warnings}"
        )


class ConformanceLayer:
    """
    Validates and optionally corrects SDTM datasets for conformance.
    
    Features:
    - Check required variables
    - Check unique keys
    - Validate dates
    - Check interval validity
    - Domain-specific rules
    """
    
    def __init__(self, strict: bool = False):
        """
        Initialize the conformance layer.
        
        Args:
            strict: If True, raise exceptions on errors
        """
        self.strict = strict
        self.report = ConformanceReport()
    
    def validate(self, datasets: Dict[str, pd.DataFrame]) -> ConformanceReport:
        """
        Validate all datasets.
        
        Args:
            datasets: Dict mapping domain name to DataFrame
            
        Returns:
            ConformanceReport with all validation results
        """
        self.report = ConformanceReport()
        
        for domain, df in datasets.items():
            self._validate_domain(domain, df, datasets)
        
        # Cross-domain checks
        if 'SE' in datasets:
            result = check_se_gapless(datasets['SE'], datasets)
            self.report.add_result(result)
        
        if 'DM' in datasets:
            result = check_dm_arm_consistency(datasets['DM'], datasets)
            self.report.add_result(result)
        
        if self.strict and self.report.errors > 0:
            raise ValueError(f"Conformance validation failed with {self.report.errors} errors")
        
        return self.report
    
    def _validate_domain(
        self, 
        domain: str, 
        df: pd.DataFrame, 
        all_datasets: Dict[str, pd.DataFrame]
    ) -> None:
        """Validate a single domain."""
        # Check required variables
        if domain in REQUIRED_VARIABLES:
            result = check_required_variables(df, domain, REQUIRED_VARIABLES[domain])
            self.report.add_result(result)
        
        # Check unique keys
        if domain in KEY_VARIABLES:
            result = check_unique_keys(df, domain, KEY_VARIABLES[domain])
            self.report.add_result(result)
        
        # Check date validity
        if domain in DATE_VARIABLES:
            result = check_valid_dates(df, domain, DATE_VARIABLES[domain])
            self.report.add_result(result)
        
        # Check --SEQ is positive
        if domain not in ['TE', 'TA', 'TV', 'RELREC', 'TI']:  # These don't have --SEQ
            result = check_seq_positive(df, domain)
            self.report.add_result(result)
        
        # Check interval validity for domains with start/end dates
        interval_pairs = {
            'SE': ('SESTDTC', 'SEENDTC'),
            'SV': ('SVSTDTC', 'SVENDTC'),
            'MH': ('MHSTDTC', 'MHENDTC'),
            'EX': ('EXSTDTC', 'EXENDTC'),
            'CM': ('CMSTDTC', 'CMENDTC'),
            'AE': ('AESTDTC', 'AEENDTC'),
            'DM': ('RFSTDTC', 'RFENDTC'),
        }
        
        if domain in interval_pairs:
            start_var, end_var = interval_pairs[domain]
            result = check_interval_validity(df, domain, start_var, end_var)
            self.report.add_result(result)
    
    def apply_fixes(self, datasets: Dict[str, pd.DataFrame]) -> Dict[str, pd.DataFrame]:
        """
        Apply automatic fixes to datasets.
        
        Fixes include:
        - Ensure DOMAIN column matches domain name
        - Sort by key variables
        - Reset index
        
        Args:
            datasets: Dict mapping domain name to DataFrame
            
        Returns:
            Dict of fixed DataFrames
        """
        fixed = {}
        
        for domain, df in datasets.items():
            df_fixed = df.copy()
            
            # Ensure DOMAIN column is correct
            if 'DOMAIN' in df_fixed.columns:
                df_fixed['DOMAIN'] = domain
            
            # Sort by key variables
            if domain in KEY_VARIABLES:
                sort_keys = [k for k in KEY_VARIABLES[domain] if k in df_fixed.columns]
                if sort_keys:
                    df_fixed = df_fixed.sort_values(sort_keys).reset_index(drop=True)
            
            # Reset index
            df_fixed = df_fixed.reset_index(drop=True)
            
            fixed[domain] = df_fixed
        
        return fixed
    
    def derive_missing_study_days(
        self, 
        datasets: Dict[str, pd.DataFrame]
    ) -> Dict[str, pd.DataFrame]:
        """
        Derive missing --DY variables from --DTC and DM.RFSTDTC.
        
        Args:
            datasets: Dict mapping domain name to DataFrame
            
        Returns:
            Dict with derived study days
        """
        from ..utils.dates import parse_date, derive_study_day
        
        if 'DM' not in datasets:
            return datasets
        
        dm_df = datasets['DM']
        
        # Build USUBJID -> RFSTDTC lookup
        rfstdtc_lookup = {}
        for _, row in dm_df.iterrows():
            usubjid = row.get('USUBJID')
            rfstdtc = row.get('RFSTDTC')
            if usubjid and rfstdtc:
                rfstdtc_lookup[usubjid] = parse_date(str(rfstdtc))
        
        derived = {}
        
        for domain, df in datasets.items():
            if domain == 'DM':
                derived[domain] = df
                continue
            
            df_derived = df.copy()
            
            # Find --DTC and --DY variable pairs
            dtc_dy_pairs = [
                ('SESTDTC', 'SESTDY'), ('SEENDTC', 'SEENDY'),
                ('SVSTDTC', 'SVSTDY'), ('SVENDTC', 'SVENDY'),
                ('DSSTDTC', 'DSDY'), ('DSDTC', 'DSDY'),
                ('MHSTDTC', 'MHSTDY'), ('MHENDTC', 'MHENDY'),
                ('EXSTDTC', 'EXSTDY'), ('EXENDTC', 'EXENDY'),
                ('CMSTDTC', 'CMSTDY'), ('CMENDTC', 'CMENDY'),
                ('VSDTC', 'VSDY'),
                ('LBDTC', 'LBDY'),
                ('AESTDTC', 'AESTDY'), ('AEENDTC', 'AEENDY'),
            ]
            
            for dtc_var, dy_var in dtc_dy_pairs:
                if dtc_var in df_derived.columns:
                    # Ensure DY column exists
                    if dy_var not in df_derived.columns:
                        df_derived[dy_var] = ''
                    
                    # Derive DY where missing
                    for idx, row in df_derived.iterrows():
                        if row.get(dy_var) == '' or pd.isna(row.get(dy_var)):
                            usubjid = row.get('USUBJID')
                            dtc_val = row.get(dtc_var)
                            
                            if usubjid in rfstdtc_lookup and dtc_val:
                                dtc_date = parse_date(str(dtc_val))
                                rfstdtc = rfstdtc_lookup[usubjid]
                                
                                if dtc_date and rfstdtc:
                                    dy = derive_study_day(dtc_date, rfstdtc)
                                    df_derived.at[idx, dy_var] = dy
            
            derived[domain] = df_derived
        
        return derived
    
    def assign_epochs(
        self, 
        datasets: Dict[str, pd.DataFrame]
    ) -> Dict[str, pd.DataFrame]:
        """
        Assign EPOCH to records based on SE intervals.
        
        Args:
            datasets: Dict mapping domain name to DataFrame
            
        Returns:
            Dict with assigned epochs
        """
        from ..utils.dates import parse_date
        
        if 'SE' not in datasets:
            return datasets
        
        se_df = datasets['SE']
        
        # Build epoch intervals per subject
        epoch_intervals = {}  # usubjid -> [(start, end, epoch), ...]
        
        for _, row in se_df.iterrows():
            usubjid = row.get('USUBJID')
            start = row.get('SESTDTC')
            end = row.get('SEENDTC')
            epoch = row.get('EPOCH')
            
            if usubjid and start and epoch:
                if usubjid not in epoch_intervals:
                    epoch_intervals[usubjid] = []
                
                start_date = parse_date(str(start))
                end_date = parse_date(str(end)) if end else None
                
                if start_date:
                    epoch_intervals[usubjid].append((start_date, end_date, epoch))
        
        # Sort intervals by start date
        for usubjid in epoch_intervals:
            epoch_intervals[usubjid].sort(key=lambda x: x[0])
        
        assigned = {}
        
        for domain, df in datasets.items():
            if domain in ['TE', 'TA', 'TS', 'TV', 'SE', 'DM']:
                assigned[domain] = df
                continue
            
            df_assigned = df.copy()
            
            # Find date column for this domain
            date_cols = {
                'SV': 'SVSTDTC',
                'DS': 'DSSTDTC',
                'MH': 'MHSTDTC',
                'EX': 'EXSTDTC',
                'CM': 'CMSTDTC',
                'VS': 'VSDTC',
                'LB': 'LBDTC',
                'AE': 'AESTDTC',
            }
            
            date_col = date_cols.get(domain)
            
            if date_col and date_col in df_assigned.columns and 'EPOCH' in df_assigned.columns:
                for idx, row in df_assigned.iterrows():
                    if row.get('EPOCH') == '' or pd.isna(row.get('EPOCH')):
                        usubjid = row.get('USUBJID')
                        date_val = row.get(date_col)
                        
                        if usubjid in epoch_intervals and date_val:
                            event_date = parse_date(str(date_val))
                            
                            if event_date:
                                # Find matching epoch
                                for start, end, epoch in epoch_intervals[usubjid]:
                                    if end is None:
                                        if event_date >= start:
                                            df_assigned.at[idx, 'EPOCH'] = epoch
                                            break
                                    else:
                                        if start <= event_date <= end:
                                            df_assigned.at[idx, 'EPOCH'] = epoch
                                            break
            
            assigned[domain] = df_assigned
        
        return assigned
    
    def apply_cross_domain_repairs(
        self,
        datasets: Dict[str, pd.DataFrame]
    ) -> Dict[str, pd.DataFrame]:
        """
        Apply cross-domain repairs to ensure clean SDTM timeline spine.
        
        Repairs include:
        1. DM.RFXENDTC = max(EX.EXENDTC) for each subject
        2. DM.RFENDTC alignment with DS disposition
        3. EPOCH derivation from SE for all domains
        4. Ensure no events occur after censor date
        
        Args:
            datasets: Dict mapping domain name to DataFrame
            
        Returns:
            Dict with repaired DataFrames
        """
        from ..utils.dates import parse_date, format_iso_date
        
        repaired = {k: v.copy() for k, v in datasets.items()}
        
        # 1. Repair DM.RFXENDTC from EX
        if 'DM' in repaired and 'EX' in repaired:
            repaired['DM'] = self._repair_dm_rfxendtc(repaired['DM'], repaired['EX'])
        
        # 2. Repair DM.RFENDTC from DS
        if 'DM' in repaired and 'DS' in repaired:
            repaired['DM'] = self._repair_dm_rfendtc(repaired['DM'], repaired['DS'])
        
        # 3. Derive EPOCH from SE for all domains
        if 'SE' in repaired:
            repaired = self._derive_epochs_from_se(repaired)
        
        return repaired
    
    def _repair_dm_rfxendtc(
        self,
        dm_df: pd.DataFrame,
        ex_df: pd.DataFrame
    ) -> pd.DataFrame:
        """
        Repair DM.RFXENDTC to match max(EX.EXENDTC) for each subject.
        """
        from ..utils.dates import parse_date, format_iso_date
        
        dm_fixed = dm_df.copy()
        
        # Build max EXENDTC lookup by USUBJID
        max_exendtc = {}
        for _, row in ex_df.iterrows():
            usubjid = row.get('USUBJID')
            exendtc = row.get('EXENDTC')
            
            if usubjid and exendtc and str(exendtc).strip():
                end_date = parse_date(str(exendtc))
                if end_date:
                    if usubjid not in max_exendtc or end_date > max_exendtc[usubjid]:
                        max_exendtc[usubjid] = end_date
        
        # Update DM.RFXENDTC
        for idx, row in dm_fixed.iterrows():
            usubjid = row.get('USUBJID')
            if usubjid in max_exendtc:
                dm_fixed.at[idx, 'RFXENDTC'] = format_iso_date(max_exendtc[usubjid])
        
        return dm_fixed
    
    def _repair_dm_rfendtc(
        self,
        dm_df: pd.DataFrame,
        ds_df: pd.DataFrame
    ) -> pd.DataFrame:
        """
        Repair DM.RFENDTC to match DS disposition date for each subject.
        """
        from ..utils.dates import parse_date, format_iso_date
        
        dm_fixed = dm_df.copy()
        
        # Build disposition date lookup by USUBJID
        # Only consider disposition events (not milestones)
        disp_dates = {}
        for _, row in ds_df.iterrows():
            usubjid = row.get('USUBJID')
            dscat = row.get('DSCAT', '')
            dsdecod = row.get('DSDECOD', '')
            dsdtc = row.get('DSDTC')
            
            # Disposition events (not protocol milestones)
            if usubjid and dsdtc and dscat != 'PROTOCOL MILESTONE':
                if dsdecod in ['COMPLETED', 'SCREEN FAILURE'] or 'ADVERSE' in str(dsdecod) or 'WITHDRAW' in str(dsdecod) or 'LOST' in str(dsdecod):
                    disp_date = parse_date(str(dsdtc))
                    if disp_date:
                        # Use the latest disposition date
                        if usubjid not in disp_dates or disp_date > disp_dates[usubjid]:
                            disp_dates[usubjid] = disp_date
        
        # Update DM.RFENDTC (skip screen failures — they must have blank RFENDTC/RFPENDTC)
        for idx, row in dm_fixed.iterrows():
            usubjid = row.get('USUBJID')
            if row.get('ARMNRS') == 'SCREEN FAILURE':
                continue
            if usubjid in disp_dates:
                dm_fixed.at[idx, 'RFENDTC'] = format_iso_date(disp_dates[usubjid])
                if 'RFPENDTC' in dm_fixed.columns:
                    dm_fixed.at[idx, 'RFPENDTC'] = format_iso_date(disp_dates[usubjid])
        
        return dm_fixed
    
    def _derive_epochs_from_se(
        self,
        datasets: Dict[str, pd.DataFrame]
    ) -> Dict[str, pd.DataFrame]:
        """
        Derive EPOCH for all domains from SE element intervals.
        Uses half-open interval logic [start, end) for non-last elements.
        """
        from ..utils.dates import parse_date
        
        se_df = datasets.get('SE')
        if se_df is None or se_df.empty:
            return datasets
        
        # Build subject -> sorted intervals lookup
        # Each interval: (start_date, end_date, epoch, is_last)
        subject_intervals = {}
        
        for usubjid in se_df['USUBJID'].unique():
            subj_se = se_df[se_df['USUBJID'] == usubjid].sort_values('SESEQ')
            intervals = []
            
            for idx, (_, row) in enumerate(subj_se.iterrows()):
                start = parse_date(str(row.get('SESTDTC', ''))) if row.get('SESTDTC') else None
                end = parse_date(str(row.get('SEENDTC', ''))) if row.get('SEENDTC') else None
                epoch = row.get('EPOCH', '')
                is_last = (idx == len(subj_se) - 1)
                
                if start:
                    intervals.append((start, end, epoch, is_last))
            
            subject_intervals[usubjid] = intervals
        
        # Domain -> date column mapping
        domain_date_cols = {
            'SV': 'SVSTDTC',
            'DS': 'DSDTC',
            'EX': 'EXSTDTC',
            'CM': 'CMSTDTC',
            'VS': 'VSDTC',
            'LB': 'LBDTC',
            'AE': 'AESTDTC',
            'MH': 'MHSTDTC',
        }
        
        repaired = {}
        for domain, df in datasets.items():
            if domain not in domain_date_cols:
                repaired[domain] = df
                continue
            
            date_col = domain_date_cols[domain]
            if date_col not in df.columns or 'EPOCH' not in df.columns:
                repaired[domain] = df
                continue
            
            df_repaired = df.copy()
            
            for idx, row in df_repaired.iterrows():
                usubjid = row.get('USUBJID')
                date_val = row.get(date_col)
                
                if usubjid not in subject_intervals or not date_val:
                    continue
                
                event_date = parse_date(str(date_val))
                if not event_date:
                    continue
                
                # Find matching epoch using half-open intervals
                for start, end, epoch, is_last in subject_intervals[usubjid]:
                    if end is None:
                        if event_date >= start:
                            df_repaired.at[idx, 'EPOCH'] = epoch
                            break
                    elif is_last:
                        # Last element: inclusive [start, end]
                        if start <= event_date <= end:
                            df_repaired.at[idx, 'EPOCH'] = epoch
                            break
                    else:
                        # Non-last elements: half-open [start, end)
                        if start <= event_date < end:
                            df_repaired.at[idx, 'EPOCH'] = epoch
                            break
            
            repaired[domain] = df_repaired
        
        return repaired
