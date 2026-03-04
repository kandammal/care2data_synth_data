"""
SDTM Validation Module

Provides validation rules that mirror Pinnacle 21 checks.
Run this before export to catch issues early.
"""

import pandas as pd
from typing import Dict, List, Tuple
from datetime import datetime
from collections import defaultdict


class ValidationResult:
    """Container for validation results."""
    
    def __init__(self):
        self.errors = []
        self.warnings = []
        self.info = []
        self.counts = defaultdict(int)
    
    def add_error(self, rule_id: str, domain: str, message: str, count: int = 1):
        self.errors.append({'rule_id': rule_id, 'domain': domain, 'message': message, 'count': count})
        self.counts[rule_id] += count
    
    def add_warning(self, rule_id: str, domain: str, message: str, count: int = 1):
        self.warnings.append({'rule_id': rule_id, 'domain': domain, 'message': message, 'count': count})
        self.counts[rule_id] += count
    
    def add_info(self, rule_id: str, domain: str, message: str, count: int = 1):
        self.info.append({'rule_id': rule_id, 'domain': domain, 'message': message, 'count': count})
        self.counts[rule_id] += count
    
    def summary(self) -> str:
        lines = [
            "=" * 80,
            "VALIDATION SUMMARY",
            "=" * 80,
            f"Errors: {len(self.errors)}",
            f"Warnings: {len(self.warnings)}",
            f"Info: {len(self.info)}",
            "",
            "Issue Counts by Rule ID:",
        ]
        for rule_id, count in sorted(self.counts.items()):
            lines.append(f"  {rule_id}: {count}")
        return "\n".join(lines)
    
    def has_errors(self) -> bool:
        return len(self.errors) > 0


# Valid codelists for validation
FREQUENCY_CODELIST = ['QD', 'BID', 'TID', 'QID', 'QW', 'Q2W', 'Q3W', 'Q4W', 'QM', 'QOD', 'PRN', 'ONCE', 'CONTINUOUS']
UNIT_CODELIST = ['mg', 'g', 'kg', 'ug', 'ng', 'mL', 'L', 'uL', 'mg/kg', 'mg/m2', 'ug/m2', 'mg/mL', 'g/L', 'g/dL', 
                 'mg/dL', 'ug/dL', 'ug/L', 'ng/mL', 'pg/mL', '10^9/L', '10^12/L', '10^6/L', '/uL',
                 'mmol/L', 'umol/L', 'mEq/L', '%', '[iU]', '[iU]/L', '[iU]/mL', 'U/L', 'mm[Hg]', 
                 'kPa', 'Cel', '/min', '/s', 'cm', 'm', 'mm', '{tbl}', '{cps}', '{dose}']


def validate_datasets(datasets: Dict[str, pd.DataFrame]) -> ValidationResult:
    """Run all validation rules on datasets."""
    result = ValidationResult()
    
    dm_df = datasets.get('DM')
    
    # Run domain-specific validations
    for domain, df in datasets.items():
        validate_domain(domain, df, dm_df, result)
    
    # Run cross-domain validations
    validate_cross_domain(datasets, result)
    
    return result


def validate_domain(domain: str, df: pd.DataFrame, dm_df: pd.DataFrame, 
                    result: ValidationResult):
    """Run validation rules for a specific domain."""
    
    # Common validations
    validate_required_columns(domain, df, result)
    validate_column_order(domain, df, result)
    
    # Domain-specific validations
    if domain == 'DM':
        validate_dm(df, result)
    elif domain == 'AE':
        validate_ae(df, dm_df, result)
    elif domain == 'CM':
        validate_cm(df, dm_df, result)
    elif domain == 'MH':
        validate_mh(df, dm_df, result)
    elif domain == 'EX':
        validate_ex(df, result)
    elif domain == 'DS':
        validate_ds(df, dm_df, result)
    elif domain == 'LB':
        validate_lb(df, result)
    elif domain == 'VS':
        validate_vs(df, result)
    elif domain == 'TS':
        validate_ts(df, result)


def validate_required_columns(domain: str, df: pd.DataFrame, result: ValidationResult):
    """Check for required columns (SD1149)."""
    required = {
        'DM': ['STUDYID', 'DOMAIN', 'USUBJID', 'SUBJID', 'SITEID', 'AGE', 'SEX'],
        'AE': ['STUDYID', 'DOMAIN', 'USUBJID', 'AESEQ', 'AETERM', 'AESTDTC'],
        'CM': ['STUDYID', 'DOMAIN', 'USUBJID', 'CMSEQ', 'CMTRT'],
        'MH': ['STUDYID', 'DOMAIN', 'USUBJID', 'MHSEQ', 'MHTERM'],
        'EX': ['STUDYID', 'DOMAIN', 'USUBJID', 'EXSEQ', 'EXTRT', 'EXSTDTC'],
        'DS': ['STUDYID', 'DOMAIN', 'USUBJID', 'DSSEQ', 'DSTERM', 'DSDECOD'],
        'LB': ['STUDYID', 'DOMAIN', 'USUBJID', 'LBSEQ', 'LBTESTCD', 'LBTEST'],
        'VS': ['STUDYID', 'DOMAIN', 'USUBJID', 'VSSEQ', 'VSTESTCD', 'VSTEST'],
        'TS': ['STUDYID', 'DOMAIN', 'TSSEQ', 'TSPARMCD', 'TSPARM', 'TSVAL'],
    }
    
    if domain in required:
        missing = [col for col in required[domain] if col not in df.columns]
        if missing:
            result.add_error('SD1149', domain, f"Missing required columns: {missing}")


def validate_column_order(domain: str, df: pd.DataFrame, result: ValidationResult):
    """Check column order (SD1079)."""
    if 'STUDYID' in df.columns and 'DOMAIN' in df.columns:
        cols = list(df.columns)
        if cols[0] != 'STUDYID':
            result.add_warning('SD1079', domain, "STUDYID should be first column")
        if cols[1] != 'DOMAIN':
            result.add_warning('SD1079', domain, "DOMAIN should be second column")


def validate_dm(df: pd.DataFrame, result: ValidationResult):
    """Validate DM domain."""
    
    # SD1031: RFENDTC should be populated
    if 'RFENDTC' in df.columns:
        null_rfendtc = df['RFENDTC'].isna() | (df['RFENDTC'] == '')
        if null_rfendtc.any():
            result.add_error('SD1031', 'DM', 
                           f"RFENDTC is null for {null_rfendtc.sum()} subjects",
                           null_rfendtc.sum())
    else:
        result.add_error('SD1149', 'DM', "RFENDTC column missing")
    
    # SD1363/SD2237: Screen failure ARM handling
    if 'ARMCD' in df.columns and 'ARMNRS' in df.columns:
        screen_fail = df[df['ARMNRS'].str.contains('SCREEN', na=False, case=False)]
        if len(screen_fail) > 0:
            bad_arm = screen_fail[(screen_fail['ARMCD'].notna()) & (screen_fail['ARMCD'] != '')]
            if len(bad_arm) > 0:
                result.add_warning('SD1363', 'DM', 
                                 f"{len(bad_arm)} screen failures have ARMCD populated")


def validate_ae(df: pd.DataFrame, dm_df: pd.DataFrame, result: ValidationResult):
    """Validate AE domain."""
    
    # SD0021: Missing end value
    if 'AEENDTC' in df.columns:
        no_endtc = df['AEENDTC'].isna() | (df['AEENDTC'] == '')
        if 'AEENRF' in df.columns:
            no_enrf = df['AEENRF'].isna() | (df['AEENRF'] == '')
            no_end_info = no_endtc & no_enrf
            if no_end_info.any():
                result.add_error('SD0021', 'AE', 
                               f"{no_end_info.sum()} records missing both AEENDTC and AEENRF",
                               no_end_info.sum())
        elif no_endtc.any():
            result.add_warning('SD0021', 'AE', 
                             f"{no_endtc.sum()} records missing AEENDTC (and AEENRF column missing)")
    
    # SD0009: SAE qualifiers
    if 'AESER' in df.columns:
        sae_cols = ['AESDTH', 'AESLIFE', 'AESHOSP', 'AESDISAB', 'AESCONG', 'AESMIE']
        existing_sae_cols = [c for c in sae_cols if c in df.columns]
        
        serious_ae = df[df['AESER'] == 'Y']
        if len(serious_ae) > 0 and existing_sae_cols:
            for idx, row in serious_ae.iterrows():
                has_qualifier = any(row.get(col) == 'Y' for col in existing_sae_cols)
                if not has_qualifier:
                    result.add_error('SD0009', 'AE', 
                                   "Serious AE without seriousness qualifier", 1)
    
    # SD1449: MedDRA coding
    meddra_cols = ['AELLT', 'AELLTCD', 'AEDECOD', 'AEPTCD', 'AEBODSYS', 'AEBDSYCD']
    if 'AETERM' in df.columns:
        for col in meddra_cols:
            if col in df.columns:
                null_vals = df[col].isna() | (df[col] == '')
                if null_vals.any():
                    result.add_warning('SD1449', 'AE', 
                                     f"{col} has {null_vals.sum()} null values",
                                     null_vals.sum())


def validate_cm(df: pd.DataFrame, dm_df: pd.DataFrame, result: ValidationResult):
    """Validate CM domain."""
    validate_end_value(df, 'CM', result)
    
    if 'CMDOSU' in df.columns:
        for val in df['CMDOSU'].dropna().unique():
            if val and val not in UNIT_CODELIST:
                result.add_warning('CT2002', 'CM', 
                                 f"CMDOSU value '{val}' not in standard codelist")


def validate_mh(df: pd.DataFrame, dm_df: pd.DataFrame, result: ValidationResult):
    """Validate MH domain."""
    validate_end_value(df, 'MH', result)


def validate_ex(df: pd.DataFrame, result: ValidationResult):
    """Validate EX domain."""
    if 'EXDOSFRQ' in df.columns:
        for val in df['EXDOSFRQ'].dropna().unique():
            if val and val not in FREQUENCY_CODELIST:
                result.add_error('CT2002', 'EX', 
                               f"EXDOSFRQ value '{val}' not in standard codelist")
    
    if 'EXDOSU' in df.columns:
        for val in df['EXDOSU'].dropna().unique():
            if val and val not in UNIT_CODELIST:
                result.add_warning('CT2002', 'EX', 
                                 f"EXDOSU value '{val}' not in standard codelist")


def validate_ds(df: pd.DataFrame, dm_df: pd.DataFrame, result: ValidationResult):
    """Validate DS domain."""
    if 'DSSTDTC' in df.columns and 'DSSTDY' in df.columns:
        has_stdtc = df['DSSTDTC'].notna() & (df['DSSTDTC'] != '')
        has_stdy = df['DSSTDY'].notna() & (df['DSSTDY'] != '')
        missing_stdy = has_stdtc & ~has_stdy
        if missing_stdy.any():
            result.add_warning('SD1088', 'DS', 
                             f"{missing_stdy.sum()} records missing DSSTDY when DSSTDTC exists",
                             missing_stdy.sum())


def validate_lb(df: pd.DataFrame, result: ValidationResult):
    """Validate LB domain."""
    for col in ['LBORNRLO', 'LBORNRHI', 'LBLOBXFL']:
        if col not in df.columns:
            result.add_info('SD0057', 'LB', f"Expected variable {col} not found")


def validate_vs(df: pd.DataFrame, result: ValidationResult):
    """Validate VS domain."""
    if 'VSLOBXFL' not in df.columns:
        result.add_info('SD0057', 'VS', "Expected variable VSLOBXFL not found")


def validate_ts(df: pd.DataFrame, result: ValidationResult):
    """Validate TS domain."""
    if 'TSPARMCD' in df.columns:
        has_sendtc = (df['TSPARMCD'] == 'SENDTC').any()
        if not has_sendtc:
            result.add_error('SD2233', 'TS', "Missing SENDTC parameter")
        
        has_dcutdtc = (df['TSPARMCD'] == 'DCUTDTC').any()
        if not has_dcutdtc:
            result.add_warning('SD2226', 'TS', "Missing DCUTDTC parameter")
    
    for col in ['TSGRPID', 'TSVALNF']:
        if col in df.columns:
            if df[col].isna().all() or (df[col] == '').all():
                result.add_info('SD1078', 'TS', 
                              f"Permissible variable {col} has all null values")


def validate_end_value(df: pd.DataFrame, domain: str, result: ValidationResult):
    """SD0021: Validate end value logic."""
    prefix = domain[:2]
    endtc_col = f'{prefix}ENDTC'
    enrf_col = f'{prefix}ENRF'
    
    if endtc_col in df.columns:
        no_endtc = df[endtc_col].isna() | (df[endtc_col] == '')
        if enrf_col in df.columns:
            no_enrf = df[enrf_col].isna() | (df[enrf_col] == '')
            no_end_info = no_endtc & no_enrf
            if no_end_info.any():
                result.add_error('SD0021', domain, 
                               f"{no_end_info.sum()} records missing both {endtc_col} and {enrf_col}",
                               no_end_info.sum())


def validate_cross_domain(datasets: Dict[str, pd.DataFrame], result: ValidationResult):
    """Run cross-domain validation rules."""
    dm_df = datasets.get('DM')
    if dm_df is None:
        return
    
    dm_subjects = set(dm_df['USUBJID'].unique())
    
    for domain, df in datasets.items():
        if domain == 'DM' or 'USUBJID' not in df.columns:
            continue
        
        domain_subjects = set(df['USUBJID'].unique())
        orphan_subjects = domain_subjects - dm_subjects
        
        if orphan_subjects:
            result.add_error('SD0002', domain, 
                           f"{len(orphan_subjects)} subjects not in DM",
                           len(orphan_subjects))


def generate_diff_report(old_result: ValidationResult, 
                         new_result: ValidationResult) -> str:
    """Generate a diff report comparing two validation runs."""
    lines = [
        "=" * 80,
        "VALIDATION DIFF REPORT",
        "=" * 80,
    ]
    
    all_rules = set(old_result.counts.keys()) | set(new_result.counts.keys())
    
    improved = []
    regressed = []
    unchanged = []
    
    for rule in sorted(all_rules):
        old_count = old_result.counts.get(rule, 0)
        new_count = new_result.counts.get(rule, 0)
        
        if new_count < old_count:
            improved.append((rule, old_count, new_count))
        elif new_count > old_count:
            regressed.append((rule, old_count, new_count))
        else:
            unchanged.append((rule, old_count, new_count))
    
    if improved:
        lines.append("\nIMPROVED (fewer issues):")
        for rule, old, new in improved:
            lines.append(f"  {rule}: {old} -> {new} (down {old - new})")
    
    if regressed:
        lines.append("\nREGRESSED (more issues):")
        for rule, old, new in regressed:
            lines.append(f"  {rule}: {old} -> {new} (up {new - old})")
    
    if unchanged:
        lines.append("\nUNCHANGED:")
        for rule, old, new in unchanged:
            if old > 0:
                lines.append(f"  {rule}: {old}")
    
    return "\n".join(lines)
