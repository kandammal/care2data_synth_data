"""
CDISC Controlled Terminology Module

Hard-coded codelists for SDTM domains to ensure CT compliance.
These should be sampled from at generation time, not patched afterward.

Source: CDISC SDTM/CDASH Controlled Terminology
"""

from typing import List, Dict, Optional
import random

# =============================================================================
# FREQUENCY (FREQ) Codelist - for EXDOSFRQ, CMDOSFRQ
# Source: CDISC CT FREQ codelist
# =============================================================================
FREQUENCY_CT = [
    # Common frequencies
    'QD',           # Once daily
    'BID',          # Twice daily  
    'TID',          # Three times daily
    'QID',          # Four times daily
    'QM',           # Once monthly
    'QOD',          # Every other day
    'PRN',          # As needed
    'ONCE',         # Single administration
    'CONTINUOUS',   # Continuous
    # Hourly frequencies
    'Q2H',          # Every 2 hours
    'Q4H',          # Every 4 hours
    'Q6H',          # Every 6 hours
    'Q8H',          # Every 8 hours
    'Q12H',         # Every 12 hours
    'Q24H',         # Every 24 hours
    # Weekly frequencies
    'Q7D',          # Every 7 days (weekly)
    'Q2M',          # Every 2 months
    'Q3M',          # Every 3 months
    # Per-week descriptions
    '1 TIME PER WEEK',
    '2 TIMES PER WEEK',
    '3 TIMES PER WEEK',
    'EVERY 2 WEEKS',
    'EVERY 3 WEEKS',
    'EVERY 4 WEEKS',
    # Morning/evening
    'QAM',          # Every morning
    'QPM',          # Every evening
    'QHS',          # At bedtime
    # Other
    'INTERMITTENT',
    'UNKNOWN',
]

# EXDOSFRQ subset (more restricted for exposure domain)
EXDOSFRQ_CT = [
    'BID', 'PRN', 'QD', 'QID', 'QM', 'QOD', 'TID', 'UNKNOWN'
]

# Map common text descriptions to CT codes
FREQUENCY_MAP = {
    'ONCE DAILY': 'QD',
    'DAILY': 'QD',
    'TWICE DAILY': 'BID',
    'TWICE A DAY': 'BID',
    'THREE TIMES DAILY': 'TID',
    'THREE TIMES A DAY': 'TID',
    'FOUR TIMES DAILY': 'QID',
    'ONCE WEEKLY': 'Q7D',
    'WEEKLY': 'Q7D',
    'QW': 'Q7D',  # Map QW to Q7D per CDISC CT
    'EVERY 2 WEEKS': 'EVERY 2 WEEKS',
    'EVERY TWO WEEKS': 'EVERY 2 WEEKS',
    'Q2W': 'EVERY 2 WEEKS',
    'BIWEEKLY': 'EVERY 2 WEEKS',
    'EVERY 3 WEEKS': 'EVERY 3 WEEKS',
    'EVERY THREE WEEKS': 'EVERY 3 WEEKS',
    'Q3W': 'EVERY 3 WEEKS',
    'EVERY 4 WEEKS': 'EVERY 4 WEEKS',
    'EVERY FOUR WEEKS': 'EVERY 4 WEEKS',
    'Q4W': 'EVERY 4 WEEKS',
    'MONTHLY': 'QM',
    'EVERY OTHER DAY': 'QOD',
    'AS NEEDED': 'PRN',
    'SINGLE DOSE': 'ONCE',
    'ONE TIME': 'ONCE',
}


# =============================================================================
# UNIT Codelist - for CMDOSU, EXDOSU
# Source: CDISC CT UNIT and CMDOSU codelists
# Note: For mass units (mg, g), CDISC references UCUM as external standard
# =============================================================================

# CMDOSU specific values from CDISC CDASH CT
CMDOSU_CT = [
    'CAPSULE',      # C48480
    'IU',           # C48579 - International Unit  
    'PUFF',         # C65060
    'TABLET',       # C48542
]

# Extended UNIT codelist from CDISC CT (count/volume based)
UNIT_CT_CDISC = [
    'ACTUATION',
    'AMPULE',
    'BAG',
    'BOTTLE',
    'CAPSULE',
    'CARTRIDGE',
    'DROP',
    'FILM',
    'GLASS',
    'IMPLANT',
    'INHALATION',
    'INJECTION',
    'IU',
    'IU/L',
    'L',
    'LOZENGE',
    'PATCH',
    'PELLET',
    'PILL',
    'PUFF',
    'SACHET',
    'SPRAY',
    'SYRINGE',
    'TABLET',
    'TROCHE',
    'VIAL',
]

# UCUM-based units (external standard referenced by CDISC for mass/concentration)
# These are valid but come from UCUM, not CDISC CT directly
UNIT_CT_UCUM = [
    'mg',           # milligram
    'g',            # gram
    'kg',           # kilogram
    'ug',           # microgram (UCUM: μg)
    'ng',           # nanogram
    'mL',           # milliliter
    'L',            # liter
    'mg/kg',        # milligram per kilogram
    'mg/m2',        # milligram per square meter
    '%',            # percent
    'cm',           # centimeter
    'mm',           # millimeter
    'mmHg',         # millimeters of mercury (CDISC preferred over mm[Hg])
    '/min',         # per minute (for heart rate, resp rate)
    'Cel',          # Celsius
    'kg/m2',        # kg per square meter (BMI)
    'g/dL',         # gram per deciliter
    'g/L',          # gram per liter
    'mmol/L',       # millimoles per liter
    'umol/L',       # micromoles per liter
    'U/L',          # units per liter
    '10*9/L',       # billions per liter (WBC, platelets)
    '10*12/L',      # trillions per liter (RBC)
]

# Combined for general use - prefer CDISC CT values
UNIT_CT = UNIT_CT_CDISC + UNIT_CT_UCUM

# Map common text to CT codes - updated for CDISC CT compliance
UNIT_MAP = {
    'MG': 'mg',
    'MILLIGRAM': 'mg',
    'MILLIGRAMS': 'mg',
    'G': 'g',
    'GRAM': 'g',
    'GRAMS': 'g',
    'KG': 'kg',
    'KILOGRAM': 'kg',
    'MCG': 'ug',
    'UG': 'ug',
    'MICROGRAM': 'ug',
    'ML': 'mL',
    'MILLILITER': 'mL',
    'L': 'L',
    'LITER': 'L',
    'MG/KG': 'mg/kg',
    'IU': 'IU',           # CDISC CT uses 'IU' not '[iU]'
    'INTERNATIONAL UNIT': 'IU',
    '[IU]': 'IU',
    'PERCENT': '%',
    'TABLET': 'TABLET',   # CDISC CT uses 'TABLET' not '{tbl}'
    'TABLETS': 'TABLET',
    '{TBL}': 'TABLET',
    'CAPSULE': 'CAPSULE', # CDISC CT uses 'CAPSULE' not '{cps}'
    'CAPSULES': 'CAPSULE',
    '{CPS}': 'CAPSULE',
    'CM': 'cm',
    'CENTIMETER': 'cm',
    'MM': 'mm',
    'MILLIMETER': 'mm',
    'MMHG': 'mmHg',       # CDISC prefers 'mmHg' over 'mm[Hg]'
    'MM[HG]': 'mmHg',
    'BPM': '/min',
    'BEATS/MIN': '/min',
    'BEATS PER MINUTE': '/min',
    '/MIN': '/min',
    'C': 'Cel',
    'CELSIUS': 'Cel',
    'DEGREES CELSIUS': 'Cel',
}


# =============================================================================
# YES/NO (NY) Codelist
# =============================================================================
NY_CT = ['Y', 'N']


# =============================================================================
# ROUTE Codelist - for EXROUTE, CMROUTE
# =============================================================================
ROUTE_CT = [
    'ORAL',
    'INTRAVENOUS',
    'SUBCUTANEOUS',
    'INTRAMUSCULAR',
    'TOPICAL',
    'TRANSDERMAL',
    'INHALATION',
    'RECTAL',
    'SUBLINGUAL',
    'INTRADERMAL',
    'OPHTHALMIC',
    'OTIC',
    'NASAL',
]


# =============================================================================
# DOSE FORM Codelist - for EXDOSFRM, CMDOSFRM
# =============================================================================
DOSE_FORM_CT = [
    'TABLET',
    'CAPSULE',
    'SOLUTION',
    'SUSPENSION',
    'INJECTION',
    'CREAM',
    'OINTMENT',
    'GEL',
    'PATCH',
    'POWDER',
    'SUPPOSITORY',
    'SPRAY',
    'DROPS',
    'FILM',
]


# =============================================================================
# SEVERITY (SEV) Codelist - for AESEV
# =============================================================================
SEVERITY_CT = ['MILD', 'MODERATE', 'SEVERE']


# =============================================================================
# OUTCOME (OUT) Codelist - for AEOUT
# =============================================================================
OUTCOME_CT = [
    'RECOVERED/RESOLVED',
    'RECOVERING/RESOLVING',
    'NOT RECOVERED/NOT RESOLVED',
    'RECOVERED/RESOLVED WITH SEQUELAE',
    'FATAL',
    'UNKNOWN',
]


# =============================================================================
# ACTION TAKEN (ACN) Codelist - for AEACN
# =============================================================================
ACTION_CT = [
    'DRUG WITHDRAWN',
    'DOSE REDUCED',
    'DOSE INCREASED',
    'DOSE NOT CHANGED',
    'DRUG INTERRUPTED',
    'NOT APPLICABLE',
    'UNKNOWN',
]


# =============================================================================
# RELATIONSHIP (REL) Codelist - for AEREL, CMDECOD related
# =============================================================================
RELATIONSHIP_CT = [
    'NOT RELATED',
    'UNLIKELY RELATED',
    'POSSIBLY RELATED',
    'PROBABLY RELATED',
    'RELATED',
]


# =============================================================================
# DISPOSITION (DSDECOD) Codelist
# =============================================================================
DISPOSITION_CT = [
    'COMPLETED',
    'SCREEN FAILURE',
    'ADVERSE EVENT',
    'DEATH',
    'LACK OF EFFICACY',
    'LOST TO FOLLOW-UP',
    'PHYSICIAN DECISION',
    'PREGNANCY',
    'PROTOCOL DEVIATION',
    'PROTOCOL VIOLATION',
    'SPONSOR DECISION',
    'STUDY TERMINATED BY SPONSOR',
    'WITHDRAWAL BY SUBJECT',
]


# =============================================================================
# END RELATIVE TO REF PERIOD (--ENRF) Codelist
# =============================================================================
ENRF_CT = [
    'BEFORE',
    'DURING',
    'AFTER',
    'ONGOING',
    'U',  # Unknown
]


# =============================================================================
# SEX Codelist
# =============================================================================
SEX_CT = ['M', 'F', 'U', 'UNDIFFERENTIATED']


# =============================================================================
# RACE Codelist
# =============================================================================
RACE_CT = [
    'WHITE',
    'BLACK OR AFRICAN AMERICAN',
    'ASIAN',
    'AMERICAN INDIAN OR ALASKA NATIVE',
    'NATIVE HAWAIIAN OR OTHER PACIFIC ISLANDER',
    'OTHER',
    'MULTIPLE',
    'NOT REPORTED',
    'UNKNOWN',
]


# =============================================================================
# ETHNICITY Codelist
# =============================================================================
ETHNICITY_CT = [
    'HISPANIC OR LATINO',
    'NOT HISPANIC OR LATINO',
    'NOT REPORTED',
    'UNKNOWN',
]


# =============================================================================
# Lab test reference ranges
# =============================================================================
LAB_REFERENCE_RANGES = {
    'ALT': {'LBORNRLO': '7', 'LBORNRHI': '56', 'LBORRESU': 'U/L', 'LBSTRESU': 'U/L'},
    'AST': {'LBORNRLO': '10', 'LBORNRHI': '40', 'LBORRESU': 'U/L', 'LBSTRESU': 'U/L'},
    'BILI': {'LBORNRLO': '0.1', 'LBORNRHI': '1.2', 'LBORRESU': 'mg/dL', 'LBSTRESU': 'umol/L'},
    'CREAT': {'LBORNRLO': '0.7', 'LBORNRHI': '1.3', 'LBORRESU': 'mg/dL', 'LBSTRESU': 'umol/L'},
    'HGB': {'LBORNRLO': '12', 'LBORNRHI': '17.5', 'LBORRESU': 'g/dL', 'LBSTRESU': 'g/L'},
    'WBC': {'LBORNRLO': '4.5', 'LBORNRHI': '11', 'LBORRESU': '10*9/L', 'LBSTRESU': '10*9/L'},
    'PLAT': {'LBORNRLO': '150', 'LBORNRHI': '400', 'LBORRESU': '10*9/L', 'LBSTRESU': '10*9/L'},
    'ALB': {'LBORNRLO': '3.5', 'LBORNRHI': '5.5', 'LBORRESU': 'g/dL', 'LBSTRESU': 'g/L'},
    'GLUC': {'LBORNRLO': '70', 'LBORNRHI': '100', 'LBORRESU': 'mg/dL', 'LBSTRESU': 'mmol/L'},
    'CHOL': {'LBORNRLO': '0', 'LBORNRHI': '200', 'LBORRESU': 'mg/dL', 'LBSTRESU': 'mmol/L'},
    'SODIUM': {'LBORNRLO': '136', 'LBORNRHI': '145', 'LBORRESU': 'mmol/L', 'LBSTRESU': 'mmol/L'},
    'POTASSIUM': {'LBORNRLO': '3.5', 'LBORNRHI': '5.0', 'LBORRESU': 'mmol/L', 'LBSTRESU': 'mmol/L'},
    'CRP': {'LBORNRLO': '0', 'LBORNRHI': '10', 'LBORRESU': 'mg/L', 'LBSTRESU': 'mg/L'},
}


# =============================================================================
# Vital Signs reference info
# =============================================================================
VS_PARAMETERS = {
    'SYSBP': {'VSTEST': 'Systolic Blood Pressure', 'VSORRESU': 'mmHg', 'VSPOS': 'SITTING'},
    'DIABP': {'VSTEST': 'Diastolic Blood Pressure', 'VSORRESU': 'mmHg', 'VSPOS': 'SITTING'},
    'PULSE': {'VSTEST': 'Pulse Rate', 'VSORRESU': '/min', 'VSPOS': 'SITTING'},
    'RESP': {'VSTEST': 'Respiratory Rate', 'VSORRESU': '/min', 'VSPOS': 'SITTING'},
    'TEMP': {'VSTEST': 'Temperature', 'VSORRESU': 'Cel', 'VSPOS': ''},
    'HEIGHT': {'VSTEST': 'Height', 'VSORRESU': 'cm', 'VSPOS': 'STANDING'},
    'WEIGHT': {'VSTEST': 'Weight', 'VSORRESU': 'kg', 'VSPOS': ''},
    'BMI': {'VSTEST': 'Body Mass Index', 'VSORRESU': 'kg/m2', 'VSPOS': ''},
}


# =============================================================================
# Trial Summary (TS) Codelists - TSPARMCD, TSPARM, TTYPE, DICTNAM
# =============================================================================

# Canonical TSPARMCD → TSPARM mapping (CDISC CT official labels)
# This is the SINGLE SOURCE OF TRUTH for TS parameter names
# SD1070 fix: Always use this lookup, never free-text TSPARM values
TSPARMCD_TO_TSPARM = {
    'ACTSUB': 'Actual Number of Subjects',
    'ADAPT': 'Adaptive Design',
    'ADDON': 'Added on to Existing Treatments',
    'AGEMAX': 'Planned Maximum Age of Subjects',
    'AGEMIN': 'Planned Minimum Age of Subjects',
    'DCUTDESC': 'Data Cutoff Description',
    'DCUTDTC': 'Data Cutoff Date',
    'EXTTIND': 'Extension Trial Indicator',
    'FCNTRY': 'Planned Country of Investigational Sites',
    'HLTSUBJI': 'Healthy Subject Indicator',
    'INDIC': 'Trial Disease/Condition Indication',
    'INTMODEL': 'Intervention Model',
    'INTTYPE': 'Intervention Type',
    'LENGTH': 'Trial Length',
    'NARMS': 'Planned Number of Arms',
    'NCOHORT': 'Number of Cohorts',
    'OBJPRIM': 'Trial Primary Objective',
    'OBJSEC': 'Trial Secondary Objective',
    'ONGOSIND': 'Trial Ongoing Study Indicator',
    'OUTMSPRI': 'Primary Outcome Measure',
    'OUTMSSEC': 'Secondary Outcome Measure',
    'PCLAS': 'Pharmacologic Class',
    'PDPSTIND': 'Protocol Deviation Prospective Indicator',
    'PDSTIND': 'Protocol Deviation Status Indicator',
    'PIPIND': 'Protocol Indicator PIP',
    'PLESSION': 'Planned Number of Study Elements per Arm',
    'PLANSUB': 'Planned Number of Subjects',
    'RANDOM': 'Trial is Randomized',
    'RDIND': 'Rare Disease Indicator',
    'REGID': 'Registry Identifier',
    'REGIMEN': 'Dosing Regimen',  # Custom parameter
    'ROUTE': 'Route of Administration',  # Custom parameter
    'SDTMVER': 'SDTM Version',
    'SDTIGVER': 'SDTMIG Version',
    'SENDTC': 'Study End Date',
    'SEXPOP': 'Sex of Participants',
    'SPONSOR': 'Clinical Study Sponsor',
    'SSTDTC': 'Study Start Date',
    'STOPRULE': 'Study Stop Rules',
    'STUDYID': 'Study Identifier',
    'STYPE': 'Study Type',
    'SDESIGN': 'Study Design',
    'TBLIND': 'Trial Blinding Schema',
    'TCNTRL': 'Control Type',
    'TDIGRP': 'Diagnosis Group',
    'THERAREA': 'Therapeutic Area',
    'TINDTP': 'Trial Intent Type',
    'TITLE': 'Trial Title',
    'TPHASE': 'Trial Phase Classification',
    'TRT': 'Investigational Therapy or Treatment',
    'TTYPE': 'Trial Type',
}

def get_tsparm(tsparmcd: str) -> str:
    """Get the canonical TSPARM label for a TSPARMCD.
    
    SD1070 fix: Always use this function to get TSPARM values.
    Never use free-text TSPARM values.
    """
    return TSPARMCD_TO_TSPARM.get(tsparmcd, tsparmcd)

# Common TSPARMCD values (subset from CDISC CT)
TSPARMCD_CT = list(TSPARMCD_TO_TSPARM.keys())

# TSPARM - full parameter names (maps to TSPARMCD) - DEPRECATED, use TSPARMCD_TO_TSPARM
TSPARM_MAP = TSPARMCD_TO_TSPARM  # Alias for backward compatibility

# TTYPE - Trial Type Response codelist (used for TSVAL when TSPARMCD=TTYPE)
TTYPE_CT = [
    'EFFICACY A',
    'SAFETY A',
    'PHARMACOKINETIC A',
    'PHARMACODYNAMIC A',
    'BIO-AVAILABILITY A',
    'BIO-EQUIVALENCE A',
    'DOSE FINDING',
    'DOSE RESPONSE A',
    'TREATMENT',
    'PREVENTION',
    'DIAGNOSIS A',
    'TOLERABILITY A',
    'FOOD EFFECT',
    'IMMUNOGENICITY A',
    'ECG',
    'THOROUGH QT TQT',
]

# DICTNAM - Dictionary Name codelist (for TSVCDREF)
DICTNAM_CT = [
    'CDISC CT CDISC',
    'COSTART',
    'CTCAE',
    'EUDRAVIGILANCE',
    'ICD',
    'ISO',
    'LOINC',
    'MED-RT',
    'SNOMED',
    'UNII',
    'WHO ATC CLASSIFICATION',
    'WHOART',
    'WHODD UMC',
    'MEDDRA',  # Common addition
]


# =============================================================================
# Helper Functions
# =============================================================================

def normalize_frequency(value: str) -> str:
    """Convert frequency text to CT code."""
    if not value:
        return ''
    upper = str(value).upper().strip()
    return FREQUENCY_MAP.get(upper, value if value in FREQUENCY_CT else 'QD')


def normalize_unit(value: str) -> str:
    """Convert unit text to CT code."""
    if not value:
        return ''
    upper = str(value).upper().strip()
    return UNIT_MAP.get(upper, value if value in UNIT_CT else value)


def sample_frequency(rng: random.Random = None) -> str:
    """Sample a valid frequency from CT."""
    if rng is None:
        rng = random.Random()
    return rng.choice(FREQUENCY_CT)


def sample_unit(category: str = 'dose', rng: random.Random = None) -> str:
    """Sample a valid unit from CT based on category."""
    if rng is None:
        rng = random.Random()
    
    if category == 'dose':
        return rng.choice(['mg', 'g', 'ug', 'mL', 'mg/kg', 'IU'])  # IU not [iU]
    elif category == 'weight':
        return 'kg'
    elif category == 'height':
        return 'cm'
    elif category == 'temperature':
        return 'Cel'
    elif category == 'blood_pressure':
        return 'mmHg'  # mmHg not mm[Hg]
    elif category == 'rate':
        return '/min'
    else:
        return rng.choice(UNIT_CT)


def sample_severity(rng: random.Random = None) -> str:
    """Sample a valid severity from CT."""
    if rng is None:
        rng = random.Random()
    return rng.choice(SEVERITY_CT)


def sample_outcome(rng: random.Random = None) -> str:
    """Sample a valid outcome from CT."""
    if rng is None:
        rng = random.Random()
    return rng.choice(OUTCOME_CT)


def sample_action(rng: random.Random = None) -> str:
    """Sample a valid action taken from CT."""
    if rng is None:
        rng = random.Random()
    return rng.choice(ACTION_CT)


def sample_relationship(rng: random.Random = None) -> str:
    """Sample a valid relationship from CT."""
    if rng is None:
        rng = random.Random()
    return rng.choice(RELATIONSHIP_CT)


def sample_route(rng: random.Random = None) -> str:
    """Sample a valid route from CT."""
    if rng is None:
        rng = random.Random()
    return rng.choice(ROUTE_CT)


def sample_dose_form(rng: random.Random = None) -> str:
    """Sample a valid dose form from CT."""
    if rng is None:
        rng = random.Random()
    return rng.choice(DOSE_FORM_CT)


def get_lab_range(testcd: str) -> Dict[str, str]:
    """Get reference range for a lab test."""
    return LAB_REFERENCE_RANGES.get(testcd.upper(), {})


def get_vs_info(testcd: str) -> Dict[str, str]:
    """Get VS parameter info."""
    return VS_PARAMETERS.get(testcd.upper(), {})


def validate_ct_value(value: str, codelist: List[str]) -> bool:
    """Check if a value is in a codelist."""
    return value in codelist if value else True
