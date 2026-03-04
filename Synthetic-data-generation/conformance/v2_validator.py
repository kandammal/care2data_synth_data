"""
Enhanced Conformance Validator — Phase 2 (§3.4.3)

Single conformance layer with tagged categories:
  - STRUCTURAL: structural integrity (required vars, unique keys, domain consistency)
  - TEMPORAL: temporal consistency (date ordering, study day alignment)
  - TERMINOLOGY: controlled terminology (CDISC codelists, MedDRA consistency)
  - COHERENCE: cross-domain coherence (death cascade, AE↔DS, EX↔DM)
  - DERIVED: derived field accuracy (--DY, EPOCH, SEQ ordering)
"""

from __future__ import annotations
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum
import pandas as pd

from ..utils.dates import parse_date, derive_study_day


# ─── Category Tags ──────────────────────────────────────────────────────────

class ConformanceCategory(str, Enum):
    STRUCTURAL = "STRUCTURAL"
    TEMPORAL = "TEMPORAL"
    TERMINOLOGY = "TERMINOLOGY"
    COHERENCE = "COHERENCE"
    DERIVED = "DERIVED"


class Severity(str, Enum):
    ERROR = "ERROR"
    WARNING = "WARNING"
    INFO = "INFO"


@dataclass
class Finding:
    """A single conformance finding."""
    rule_id: str
    category: ConformanceCategory
    severity: Severity
    domain: str
    message: str
    affected_count: int = 0
    details: List[str] = field(default_factory=list)

    @property
    def passed(self) -> bool:
        return self.severity == Severity.INFO


@dataclass
class ConformanceResult:
    """Aggregated conformance results."""
    findings: List[Finding] = field(default_factory=list)

    @property
    def n_errors(self) -> int:
        return sum(1 for f in self.findings if f.severity == Severity.ERROR)

    @property
    def n_warnings(self) -> int:
        return sum(1 for f in self.findings if f.severity == Severity.WARNING)

    @property
    def passed(self) -> bool:
        return self.n_errors == 0

    def summary(self) -> str:
        cats = {}
        for f in self.findings:
            cats.setdefault(f.category.value, {'errors': 0, 'warnings': 0, 'infos': 0})
            cats[f.category.value][f.severity.value.lower() + 's'] += 1

        lines = [f"Conformance: {'PASS' if self.passed else 'FAIL'} "
                 f"({self.n_errors} errors, {self.n_warnings} warnings, "
                 f"{len(self.findings)} total findings)"]
        for cat, counts in sorted(cats.items()):
            lines.append(f"  {cat}: {counts['errors']}E / {counts['warnings']}W / {counts['infos']}I")
        return "\n".join(lines)

    def to_dataframe(self) -> pd.DataFrame:
        records = []
        for f in self.findings:
            records.append({
                'Rule': f.rule_id,
                'Category': f.category.value,
                'Severity': f.severity.value,
                'Domain': f.domain,
                'Message': f.message,
                'Affected': f.affected_count,
            })
        return pd.DataFrame(records) if records else pd.DataFrame(
            columns=['Rule', 'Category', 'Severity', 'Domain', 'Message', 'Affected'])


# ─── Validator ───────────────────────────────────────────────────────────────

class ConformanceValidator:
    """
    Phase 2 conformance validator with tagged categories.

    Usage:
        validator = ConformanceValidator()
        result = validator.validate(datasets)
        print(result.summary())
    """

    def validate(
        self,
        datasets: Dict[str, pd.DataFrame],
        is_crossover: bool = False,
    ) -> ConformanceResult:
        result = ConformanceResult()

        # ── STRUCTURAL checks ──
        self._check_structural(datasets, result)

        # ── TEMPORAL checks ──
        self._check_temporal(datasets, result)

        # ── TERMINOLOGY checks ──
        self._check_terminology(datasets, result)

        # ── COHERENCE checks ──
        self._check_coherence(datasets, result, is_crossover)

        # ── DERIVED checks ──
        self._check_derived(datasets, result)

        return result

    # ── STRUCTURAL ──────────────────────────────────────────────────────────

    REQUIRED_VARS = {
        'DM': ['STUDYID', 'DOMAIN', 'USUBJID', 'SUBJID', 'SITEID', 'AGE', 'SEX', 'ARMCD', 'ARM'],
        'AE': ['STUDYID', 'DOMAIN', 'USUBJID', 'AESEQ', 'AETERM', 'AEDECOD', 'AESTDTC'],
        'DS': ['STUDYID', 'DOMAIN', 'USUBJID', 'DSSEQ', 'DSTERM', 'DSDECOD', 'DSCAT'],
        'EX': ['STUDYID', 'DOMAIN', 'USUBJID', 'EXSEQ', 'EXTRT', 'EXSTDTC'],
        'CM': ['STUDYID', 'DOMAIN', 'USUBJID', 'CMSEQ', 'CMTRT'],
        'MH': ['STUDYID', 'DOMAIN', 'USUBJID', 'MHSEQ', 'MHTERM'],
        'VS': ['STUDYID', 'DOMAIN', 'USUBJID', 'VSSEQ', 'VSTESTCD', 'VSTEST'],
        'LB': ['STUDYID', 'DOMAIN', 'USUBJID', 'LBSEQ', 'LBTESTCD', 'LBTEST'],
        'SE': ['STUDYID', 'DOMAIN', 'USUBJID', 'SESEQ', 'ETCD', 'ELEMENT'],
        'SV': ['STUDYID', 'DOMAIN', 'USUBJID', 'SVSEQ', 'VISITNUM'],
    }

    UNIQUE_KEYS = {
        'DM': ['USUBJID'],
        'AE': ['USUBJID', 'AESEQ'],
        'DS': ['USUBJID', 'DSSEQ'],
        'EX': ['USUBJID', 'EXSEQ'],
        'CM': ['USUBJID', 'CMSEQ'],
        'MH': ['USUBJID', 'MHSEQ'],
        'VS': ['USUBJID', 'VSSEQ'],
        'LB': ['USUBJID', 'LBSEQ'],
        'SE': ['USUBJID', 'SESEQ'],
        'SV': ['USUBJID', 'SVSEQ'],
    }

    def _check_structural(self, datasets: Dict[str, pd.DataFrame], result: ConformanceResult):
        for domain, df in datasets.items():
            if df is None or df.empty:
                continue

            # Required variables
            req = self.REQUIRED_VARS.get(domain, [])
            missing = [v for v in req if v not in df.columns]
            if missing:
                result.findings.append(Finding(
                    rule_id=f"ST01_{domain}", category=ConformanceCategory.STRUCTURAL,
                    severity=Severity.ERROR, domain=domain,
                    message=f"Missing required variables: {missing}",
                    affected_count=len(missing),
                ))
            else:
                result.findings.append(Finding(
                    rule_id=f"ST01_{domain}", category=ConformanceCategory.STRUCTURAL,
                    severity=Severity.INFO, domain=domain,
                    message=f"All required variables present",
                ))

            # Unique keys
            keys = self.UNIQUE_KEYS.get(domain, [])
            valid_keys = [k for k in keys if k in df.columns]
            if valid_keys and len(valid_keys) == len(keys):
                dupes = df.duplicated(subset=valid_keys, keep=False)
                n_dupes = dupes.sum()
                if n_dupes > 0:
                    result.findings.append(Finding(
                        rule_id=f"ST02_{domain}", category=ConformanceCategory.STRUCTURAL,
                        severity=Severity.ERROR, domain=domain,
                        message=f"{n_dupes} duplicate key records ({keys})",
                        affected_count=n_dupes,
                    ))
                else:
                    result.findings.append(Finding(
                        rule_id=f"ST02_{domain}", category=ConformanceCategory.STRUCTURAL,
                        severity=Severity.INFO, domain=domain,
                        message=f"Unique keys valid",
                    ))

            # DOMAIN column matches
            if 'DOMAIN' in df.columns:
                mismatch = (df['DOMAIN'] != domain).sum()
                if mismatch > 0:
                    result.findings.append(Finding(
                        rule_id=f"ST03_{domain}", category=ConformanceCategory.STRUCTURAL,
                        severity=Severity.ERROR, domain=domain,
                        message=f"{mismatch} records with wrong DOMAIN value",
                        affected_count=mismatch,
                    ))

            # SEQ positive integers
            seq_col = f"{domain}SEQ"
            if seq_col in df.columns:
                non_pos = (df[seq_col].astype(float) <= 0).sum()
                if non_pos > 0:
                    result.findings.append(Finding(
                        rule_id=f"ST04_{domain}", category=ConformanceCategory.STRUCTURAL,
                        severity=Severity.ERROR, domain=domain,
                        message=f"{non_pos} records with non-positive SEQ",
                        affected_count=non_pos,
                    ))

    # ── TEMPORAL ───────────────────────────────────────────────────────────

    def _check_temporal(self, datasets: Dict[str, pd.DataFrame], result: ConformanceResult):
        # AE: start <= end
        ae = datasets.get('AE')
        if ae is not None and not ae.empty and 'AESTDTC' in ae.columns and 'AEENDTC' in ae.columns:
            n_bad = 0
            for _, row in ae.iterrows():
                st = parse_date(str(row.get('AESTDTC', '')))
                en = parse_date(str(row.get('AEENDTC', '')))
                if st and en and en < st:
                    n_bad += 1
            if n_bad > 0:
                result.findings.append(Finding(
                    rule_id="TE01_AE", category=ConformanceCategory.TEMPORAL,
                    severity=Severity.ERROR, domain="AE",
                    message=f"{n_bad} AE records with end date before start date",
                    affected_count=n_bad,
                ))
            else:
                result.findings.append(Finding(
                    rule_id="TE01_AE", category=ConformanceCategory.TEMPORAL,
                    severity=Severity.INFO, domain="AE", message="AE date intervals valid",
                ))

        # EX: start <= end
        ex = datasets.get('EX')
        if ex is not None and not ex.empty and 'EXSTDTC' in ex.columns and 'EXENDTC' in ex.columns:
            n_bad = 0
            for _, row in ex.iterrows():
                st = parse_date(str(row.get('EXSTDTC', '')))
                en = parse_date(str(row.get('EXENDTC', '')))
                if st and en and en < st:
                    n_bad += 1
            sev = Severity.ERROR if n_bad > 0 else Severity.INFO
            result.findings.append(Finding(
                rule_id="TE01_EX", category=ConformanceCategory.TEMPORAL,
                severity=sev, domain="EX",
                message=f"{'EX date intervals valid' if n_bad == 0 else f'{n_bad} EX records with end < start'}",
                affected_count=n_bad,
            ))

        # DM: RFSTDTC <= RFENDTC
        dm = datasets.get('DM')
        if dm is not None and not dm.empty and 'RFSTDTC' in dm.columns and 'RFENDTC' in dm.columns:
            n_bad = 0
            for _, row in dm.iterrows():
                st = parse_date(str(row.get('RFSTDTC', '')))
                en = parse_date(str(row.get('RFENDTC', '')))
                if st and en and en < st:
                    n_bad += 1
            sev = Severity.ERROR if n_bad > 0 else Severity.INFO
            result.findings.append(Finding(
                rule_id="TE02_DM", category=ConformanceCategory.TEMPORAL,
                severity=sev, domain="DM",
                message=f"{'DM reference intervals valid' if n_bad == 0 else f'{n_bad} DM subjects with RFENDTC < RFSTDTC'}",
                affected_count=n_bad,
            ))

        # No events after death
        if dm is not None and not dm.empty and 'DTHDTC' in dm.columns and ae is not None:
            death_dates = {}
            for _, row in dm.iterrows():
                dthdtc = parse_date(str(row.get('DTHDTC', '')))
                if dthdtc:
                    death_dates[row['USUBJID']] = dthdtc

            n_after_death = 0
            for _, row in ae.iterrows():
                subj = row.get('USUBJID')
                if subj in death_dates:
                    ae_start = parse_date(str(row.get('AESTDTC', '')))
                    if ae_start and ae_start > death_dates[subj]:
                        n_after_death += 1

            if death_dates:
                sev = Severity.ERROR if n_after_death > 0 else Severity.INFO
                result.findings.append(Finding(
                    rule_id="TE03_DEATH", category=ConformanceCategory.TEMPORAL,
                    severity=sev, domain="AE",
                    message=f"{'No AEs after death' if n_after_death == 0 else f'{n_after_death} AEs start after death date'}",
                    affected_count=n_after_death,
                ))

    # ── TERMINOLOGY ─────────────────────────────────────────────────────────

    VALID_SEV = {'MILD', 'MODERATE', 'SEVERE'}
    VALID_AEOUT = {
        'RECOVERED/RESOLVED', 'RECOVERING/RESOLVING', 'NOT RECOVERED/NOT RESOLVED',
        'RECOVERED/RESOLVED WITH SEQUELAE', 'FATAL', 'UNKNOWN',
    }
    VALID_SEX = {'M', 'F', 'U', 'UNDIFFERENTIATED'}
    VALID_AESER = {'Y', 'N'}

    def _check_terminology(self, datasets: Dict[str, pd.DataFrame], result: ConformanceResult):
        ae = datasets.get('AE')
        if ae is not None and not ae.empty:
            # AESEV
            if 'AESEV' in ae.columns:
                invalid = ae[~ae['AESEV'].isin(self.VALID_SEV)]
                n = len(invalid)
                sev = Severity.ERROR if n > 0 else Severity.INFO
                result.findings.append(Finding(
                    rule_id="CT01_AESEV", category=ConformanceCategory.TERMINOLOGY,
                    severity=sev, domain="AE",
                    message=f"{'AESEV values valid' if n == 0 else f'{n} invalid AESEV values'}",
                    affected_count=n,
                ))

            # AEOUT
            if 'AEOUT' in ae.columns:
                invalid = ae[~ae['AEOUT'].isin(self.VALID_AEOUT)]
                n = len(invalid)
                sev = Severity.ERROR if n > 0 else Severity.INFO
                result.findings.append(Finding(
                    rule_id="CT02_AEOUT", category=ConformanceCategory.TERMINOLOGY,
                    severity=sev, domain="AE",
                    message=f"{'AEOUT values valid' if n == 0 else f'{n} invalid AEOUT values'}",
                    affected_count=n,
                ))

            # AESER
            if 'AESER' in ae.columns:
                invalid = ae[~ae['AESER'].isin(self.VALID_AESER)]
                n = len(invalid)
                sev = Severity.ERROR if n > 0 else Severity.INFO
                result.findings.append(Finding(
                    rule_id="CT03_AESER", category=ConformanceCategory.TERMINOLOGY,
                    severity=sev, domain="AE",
                    message=f"{'AESER values valid' if n == 0 else f'{n} invalid AESER values'}",
                    affected_count=n,
                ))

            # MedDRA: AEDECOD populated when AETERM exists
            if 'AETERM' in ae.columns and 'AEDECOD' in ae.columns:
                has_term = ae['AETERM'].notna() & (ae['AETERM'] != '')
                missing_decod = has_term & (ae['AEDECOD'].isna() | (ae['AEDECOD'] == ''))
                n = missing_decod.sum()
                sev = Severity.WARNING if n > 0 else Severity.INFO
                result.findings.append(Finding(
                    rule_id="CT04_MEDDRA", category=ConformanceCategory.TERMINOLOGY,
                    severity=sev, domain="AE",
                    message=f"{'All AEs have AEDECOD' if n == 0 else f'{n} AEs with AETERM but no AEDECOD'}",
                    affected_count=n,
                ))

        # DM: SEX
        dm = datasets.get('DM')
        if dm is not None and not dm.empty and 'SEX' in dm.columns:
            invalid = dm[~dm['SEX'].isin(self.VALID_SEX)]
            n = len(invalid)
            sev = Severity.ERROR if n > 0 else Severity.INFO
            result.findings.append(Finding(
                rule_id="CT05_SEX", category=ConformanceCategory.TERMINOLOGY,
                severity=sev, domain="DM",
                message=f"{'SEX values valid' if n == 0 else f'{n} invalid SEX values'}",
                affected_count=n,
            ))

    # ── COHERENCE ──────────────────────────────────────────────────────────

    def _check_coherence(self, datasets: Dict[str, pd.DataFrame], result: ConformanceResult,
                         is_crossover: bool = False):
        dm = datasets.get('DM')
        ae = datasets.get('AE')
        ds = datasets.get('DS')
        ex = datasets.get('EX')

        if dm is None or dm.empty:
            return

        dm_subjects = set(dm['USUBJID'].unique())

        # All subjects in AE/DS/EX must exist in DM
        for domain_name, df in [('AE', ae), ('DS', ds), ('EX', ex)]:
            if df is not None and not df.empty and 'USUBJID' in df.columns:
                orphans = set(df['USUBJID'].unique()) - dm_subjects
                n = len(orphans)
                sev = Severity.ERROR if n > 0 else Severity.INFO
                result.findings.append(Finding(
                    rule_id=f"CO01_{domain_name}", category=ConformanceCategory.COHERENCE,
                    severity=sev, domain=domain_name,
                    message=f"{'All subjects in DM' if n == 0 else f'{n} subjects in {domain_name} but not DM'}",
                    affected_count=n,
                ))

        # Death cascade: DTHFL=Y subjects must have DS DEATH record
        if ds is not None and 'DTHFL' in dm.columns:
            dead_subs = set(dm[dm['DTHFL'] == 'Y']['USUBJID'].unique())
            ds_death = set(ds[ds['DSDECOD'] == 'DEATH']['USUBJID'].unique()) if 'DSDECOD' in ds.columns else set()
            missing_ds = dead_subs - ds_death
            n = len(missing_ds)
            if dead_subs:
                sev = Severity.ERROR if n > 0 else Severity.INFO
                result.findings.append(Finding(
                    rule_id="CO02_DEATH", category=ConformanceCategory.COHERENCE,
                    severity=sev, domain="DS",
                    message=f"{'Death cascade complete' if n == 0 else f'{n} dead subjects without DS DEATH record'}",
                    affected_count=n,
                ))

        # Fatal AE: AESDTH=Y must correspond to DTHFL=Y in DM
        if ae is not None and not ae.empty and 'AESDTH' in ae.columns:
            fatal_ae_subs = set(ae[ae['AESDTH'] == 'Y']['USUBJID'].unique())
            dead_dm = set(dm[dm.get('DTHFL', '') == 'Y']['USUBJID'].unique()) if 'DTHFL' in dm.columns else set()
            missing_dthfl = fatal_ae_subs - dead_dm
            n = len(missing_dthfl)
            if fatal_ae_subs:
                sev = Severity.ERROR if n > 0 else Severity.INFO
                result.findings.append(Finding(
                    rule_id="CO03_FATAL_AE", category=ConformanceCategory.COHERENCE,
                    severity=sev, domain="DM",
                    message=f"{'Fatal AE ↔ DM.DTHFL consistent' if n == 0 else f'{n} fatal AE subjects without DTHFL=Y'}",
                    affected_count=n,
                ))

        # Enrolled subjects must have EX records (unless screen failure)
        if ex is not None and 'ARMNRS' in dm.columns:
            enrolled = set(dm[dm['ARMNRS'] != 'SCREEN FAILURE']['USUBJID'].unique())
            has_ex = set(ex['USUBJID'].unique()) if 'USUBJID' in ex.columns else set()
            no_ex = enrolled - has_ex
            n = len(no_ex)
            sev = Severity.WARNING if n > 0 else Severity.INFO
            result.findings.append(Finding(
                rule_id="CO04_EX", category=ConformanceCategory.COHERENCE,
                severity=sev, domain="EX",
                message=f"{'All enrolled subjects have EX' if n == 0 else f'{n} enrolled subjects without EX records'}",
                affected_count=n,
            ))

        # Screen failures: RFENDTC and RFPENDTC must be blank (SD1366)
        if 'ARMNRS' in dm.columns:
            sf = dm[dm['ARMNRS'] == 'SCREEN FAILURE']
            if not sf.empty:
                bad_rfendtc = sf[sf.get('RFENDTC', pd.Series(dtype=str)).astype(str).str.strip().ne('')]
                bad_rfpendtc = sf[sf.get('RFPENDTC', pd.Series(dtype=str)).astype(str).str.strip().ne('')]
                n = len(set(bad_rfendtc.get('USUBJID', [])).union(set(bad_rfpendtc.get('USUBJID', []))))
                sev = Severity.ERROR if n > 0 else Severity.INFO
                result.findings.append(Finding(
                    rule_id="CO06_SF_DATES", category=ConformanceCategory.COHERENCE,
                    severity=sev, domain="DM",
                    message=f"{'Screen failures have blank RFENDTC/RFPENDTC' if n == 0 else f'{n} screen failures with non-blank RFENDTC/RFPENDTC'}",
                    affected_count=n,
                ))

        # Crossover: DM.ARMCD should be a sequence code, not a treatment arm
        if is_crossover and 'ARMCD' in dm.columns:
            result.findings.append(Finding(
                rule_id="CO05_XOVER", category=ConformanceCategory.COHERENCE,
                severity=Severity.INFO, domain="DM",
                message=f"Crossover design: DM.ARMCD values = {sorted(dm[dm['ARMCD'] != '']['ARMCD'].unique().tolist())}",
            ))

    # ── DERIVED ────────────────────────────────────────────────────────────

    def _check_derived(self, datasets: Dict[str, pd.DataFrame], result: ConformanceResult):
        dm = datasets.get('DM')
        if dm is None or dm.empty:
            return

        # Build RFSTDTC lookup
        rfstdtc_map = {}
        for _, row in dm.iterrows():
            rfstdtc = parse_date(str(row.get('RFSTDTC', '')))
            if rfstdtc:
                rfstdtc_map[row['USUBJID']] = rfstdtc

        # Check --DY derivation for AE
        ae = datasets.get('AE')
        if ae is not None and not ae.empty and 'AESTDY' in ae.columns and 'AESTDTC' in ae.columns:
            n_wrong = 0
            n_checked = 0
            for _, row in ae.iterrows():
                subj = row.get('USUBJID')
                if subj not in rfstdtc_map:
                    continue
                ae_date = parse_date(str(row.get('AESTDTC', '')))
                reported_dy = row.get('AESTDY')
                if ae_date and reported_dy != '' and reported_dy is not None:
                    expected = derive_study_day(ae_date, rfstdtc_map[subj])
                    n_checked += 1
                    try:
                        if int(float(reported_dy)) != expected:
                            n_wrong += 1
                    except (ValueError, TypeError):
                        n_wrong += 1

            if n_checked > 0:
                sev = Severity.ERROR if n_wrong > 0 else Severity.INFO
                result.findings.append(Finding(
                    rule_id="DV01_AESTDY", category=ConformanceCategory.DERIVED,
                    severity=sev, domain="AE",
                    message=f"{'AESTDY correctly derived' if n_wrong == 0 else f'{n_wrong}/{n_checked} AESTDY values incorrectly derived'}",
                    affected_count=n_wrong,
                ))

        # Check SEQ ordering (Contract 8): AE should be sorted by AESTDTC within USUBJID
        if ae is not None and not ae.empty and 'AESEQ' in ae.columns:
            n_misordered = 0
            for subj, grp in ae.groupby('USUBJID'):
                seqs = grp['AESEQ'].tolist()
                if seqs != sorted(seqs):
                    n_misordered += 1
            sev = Severity.WARNING if n_misordered > 0 else Severity.INFO
            result.findings.append(Finding(
                rule_id="DV02_AESEQ", category=ConformanceCategory.DERIVED,
                severity=sev, domain="AE",
                message=f"{'AESEQ monotonically increasing per subject' if n_misordered == 0 else f'{n_misordered} subjects with non-monotonic AESEQ'}",
                affected_count=n_misordered,
            ))

        # EPOCH populated
        for domain_name in ('AE', 'EX', 'VS', 'LB'):
            df = datasets.get(domain_name)
            if df is not None and not df.empty and 'EPOCH' in df.columns:
                n_empty = ((df['EPOCH'] == '') | df['EPOCH'].isna()).sum()
                if n_empty > 0 and len(df) > 0:
                    pct = n_empty / len(df) * 100
                    sev = Severity.WARNING if pct > 50 else Severity.INFO
                    result.findings.append(Finding(
                        rule_id=f"DV03_{domain_name}", category=ConformanceCategory.DERIVED,
                        severity=sev, domain=domain_name,
                        message=f"{n_empty}/{len(df)} ({pct:.0f}%) records with empty EPOCH",
                        affected_count=n_empty,
                    ))
