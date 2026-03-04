"""
CDISC SDTM Controlled Terminology

This module provides official CDISC controlled terminology codelists
for use in synthetic SDTM data generation.

Based on CDISC SDTM Terminology (NCI EVS) - aligned with 2023-12-15 release.
Each codelist includes:
- NCI C-code for the codelist
- NCI C-codes for individual terms
- CDISC Submission Values (the actual values to use in datasets)

Reference: https://www.cdisc.org/standards/terminology/controlled-terminology
"""

from typing import Dict, List, Optional, NamedTuple
from enum import Enum


class CodedTerm(NamedTuple):
    """A term with its NCI code."""
    code: str  # NCI C-code (e.g., "C25301")
    value: str  # CDISC Submission Value


class Codelist(NamedTuple):
    """A codelist with its terms."""
    code: str  # Codelist C-code
    name: str  # Codelist name
    extensible: bool  # Whether sponsor can add values
    terms: List[CodedTerm]


# =============================================================================
# DEMOGRAPHICS CODELISTS
# =============================================================================

SEX = Codelist(
    code="C66731",
    name="Sex",
    extensible=False,
    terms=[
        CodedTerm("C16576", "F"),
        CodedTerm("C20197", "M"),
        CodedTerm("C17998", "U"),
        CodedTerm("C45908", "UNDIFFERENTIATED"),
    ]
)

ETHNIC = Codelist(
    code="C66790",
    name="Ethnic Group",
    extensible=False,
    terms=[
        CodedTerm("C17459", "HISPANIC OR LATINO"),
        CodedTerm("C41222", "NOT HISPANIC OR LATINO"),
        CodedTerm("C17998", "NOT REPORTED"),
        CodedTerm("C17998", "UNKNOWN"),
    ]
)

RACE = Codelist(
    code="C74457",
    name="Race",
    extensible=True,
    terms=[
        CodedTerm("C41260", "AMERICAN INDIAN OR ALASKA NATIVE"),
        CodedTerm("C41259", "ASIAN"),
        CodedTerm("C16352", "BLACK OR AFRICAN AMERICAN"),
        CodedTerm("C41219", "NATIVE HAWAIIAN OR OTHER PACIFIC ISLANDER"),
        CodedTerm("C41261", "WHITE"),
        CodedTerm("C17649", "OTHER"),
        CodedTerm("C43234", "MULTIPLE"),
        CodedTerm("C17998", "NOT REPORTED"),
        CodedTerm("C17998", "UNKNOWN"),
    ]
)

AGEU = Codelist(
    code="C66781",
    name="Age Unit",
    extensible=False,
    terms=[
        CodedTerm("C29848", "DAYS"),
        CodedTerm("C29844", "HOURS"),
        CodedTerm("C29846", "MONTHS"),
        CodedTerm("C29840", "WEEKS"),
        CodedTerm("C29848", "YEARS"),
    ]
)

COUNTRY = Codelist(
    code="C66729",
    name="Country",
    extensible=False,  # Uses ISO 3166-1 Alpha-3
    terms=[
        CodedTerm("C17003", "USA"),
        CodedTerm("C16653", "GBR"),
        CodedTerm("C16474", "DEU"),
        CodedTerm("C16592", "FRA"),
        CodedTerm("C17272", "JPN"),
        CodedTerm("C16426", "CHN"),
        CodedTerm("C17152", "IND"),
        CodedTerm("C16352", "BRA"),
        CodedTerm("C16380", "CAN"),
        CodedTerm("C16307", "AUS"),
        CodedTerm("C17245", "ITA"),
        CodedTerm("C17427", "ESP"),
        CodedTerm("C17366", "KOR"),
        CodedTerm("C17541", "TWN"),
    ]
)

# =============================================================================
# ADVERSE EVENTS CODELISTS
# =============================================================================

AESEV = Codelist(
    code="C66769",
    name="Severity/Intensity Scale for Adverse Event",
    extensible=False,
    terms=[
        CodedTerm("C41338", "MILD"),
        CodedTerm("C41339", "MODERATE"),
        CodedTerm("C41340", "SEVERE"),
    ]
)

AESER = Codelist(
    code="C66742",
    name="No Yes Response",
    extensible=False,
    terms=[
        CodedTerm("C49487", "Y"),
        CodedTerm("C49488", "N"),
    ]
)

# AEREL - Causality
AEREL = Codelist(
    code="C66768",
    name="Relationship to Reference Intervention",
    extensible=True,
    terms=[
        CodedTerm("C53256", "NOT RELATED"),
        CodedTerm("C53259", "UNLIKELY RELATED"),
        CodedTerm("C53257", "POSSIBLY RELATED"),
        CodedTerm("C53258", "PROBABLY RELATED"),
        CodedTerm("C53260", "RELATED"),
    ]
)

AEOUT = Codelist(
    code="C66768",
    name="Outcome of Event",
    extensible=False,
    terms=[
        CodedTerm("C49494", "RECOVERED/RESOLVED"),
        CodedTerm("C49495", "RECOVERING/RESOLVING"),
        CodedTerm("C49496", "NOT RECOVERED/NOT RESOLVED"),
        CodedTerm("C49497", "RECOVERED/RESOLVED WITH SEQUELAE"),
        CodedTerm("C48275", "FATAL"),
        CodedTerm("C17998", "UNKNOWN"),
    ]
)

AEACN = Codelist(
    code="C66767",
    name="Action Taken with Study Treatment",
    extensible=True,
    terms=[
        CodedTerm("C49501", "DRUG WITHDRAWN"),
        CodedTerm("C49500", "DOSE REDUCED"),
        CodedTerm("C49498", "DOSE NOT CHANGED"),
        CodedTerm("C49502", "DOSE INCREASED"),
        CodedTerm("C49504", "DRUG INTERRUPTED"),
        CodedTerm("C17998", "UNKNOWN"),
        CodedTerm("C48660", "NOT APPLICABLE"),
    ]
)

# =============================================================================
# DISPOSITION CODELISTS
# =============================================================================

DSDECOD = Codelist(
    code="C66727",
    name="Standardized Disposition Term",
    extensible=True,
    terms=[
        CodedTerm("C25228", "COMPLETED"),
        CodedTerm("C28554", "SCREEN FAILURE"),
        CodedTerm("C49484", "ADVERSE EVENT"),
        CodedTerm("C49485", "LACK OF EFFICACY"),
        CodedTerm("C49632", "LOST TO FOLLOW-UP"),
        CodedTerm("C28532", "DEATH"),
        CodedTerm("C49633", "PHYSICIAN DECISION"),
        CodedTerm("C49634", "PROTOCOL DEVIATION"),
        CodedTerm("C49636", "SPONSOR DECISION"),
        CodedTerm("C49635", "STUDY TERMINATED BY SPONSOR"),
        CodedTerm("C49637", "WITHDRAWAL BY SUBJECT"),
        CodedTerm("C48660", "NOT APPLICABLE"),
    ]
)

DSCAT = Codelist(
    code="C74558",
    name="Disposition Category",
    extensible=True,
    terms=[
        CodedTerm("C49629", "DISPOSITION EVENT"),
        CodedTerm("C49628", "PROTOCOL MILESTONE"),
        CodedTerm("C66787", "OTHER EVENT"),
    ]
)

# =============================================================================
# EXPOSURE CODELISTS
# =============================================================================

EXROUTE = Codelist(
    code="C66729",
    name="Route of Administration",
    extensible=True,
    terms=[
        CodedTerm("C38288", "ORAL"),
        CodedTerm("C38299", "SUBCUTANEOUS"),
        CodedTerm("C38276", "INTRAVENOUS"),
        CodedTerm("C28161", "INTRAMUSCULAR"),
        CodedTerm("C38304", "TOPICAL"),
        CodedTerm("C38300", "SUBLINGUAL"),
        CodedTerm("C38284", "NASAL"),
        CodedTerm("C38216", "RESPIRATORY (INHALATION)"),
        CodedTerm("C38290", "OPHTHALMIC"),
        CodedTerm("C38285", "OTIC"),
        CodedTerm("C38295", "RECTAL"),
        CodedTerm("C38313", "VAGINAL"),
        CodedTerm("C38311", "TRANSDERMAL"),
    ]
)

EXDOSFRM = Codelist(
    code="C66726",
    name="Pharmaceutical Dosage Form",
    extensible=True,
    terms=[
        CodedTerm("C42998", "TABLET"),
        CodedTerm("C25158", "CAPSULE"),
        CodedTerm("C42944", "SOLUTION"),
        CodedTerm("C42953", "POWDER"),
        CodedTerm("C28944", "CREAM"),
        CodedTerm("C42942", "OINTMENT"),
        CodedTerm("C42920", "INJECTION"),
        CodedTerm("C42893", "AEROSOL"),
        CodedTerm("C42951", "PATCH"),
        CodedTerm("C42916", "GEL"),
        CodedTerm("C42948", "LOTION"),
        CodedTerm("C42960", "SUSPENSION"),
        CodedTerm("C42909", "FILM"),
        CodedTerm("C42962", "SYRUP"),
    ]
)

EXDOSFRQ = Codelist(
    code="C71113",
    name="Frequency",
    extensible=True,
    terms=[
        CodedTerm("C64496", "QD"),
        CodedTerm("C64499", "BID"),
        CodedTerm("C64522", "TID"),
        CodedTerm("C64527", "QID"),
        CodedTerm("C64500", "QHS"),
        CodedTerm("C64529", "PRN"),
        CodedTerm("C64530", "QOD"),
        CodedTerm("C64495", "QW"),
        CodedTerm("C64526", "Q2W"),
        CodedTerm("C64521", "Q4W"),
        CodedTerm("C64497", "ONCE"),
        CodedTerm("C64528", "CONTINUOUS"),
    ]
)

# =============================================================================
# VITAL SIGNS CODELISTS
# =============================================================================

VSTESTCD = Codelist(
    code="C66741",
    name="Vital Signs Test Code",
    extensible=True,
    terms=[
        CodedTerm("C49676", "SYSBP"),
        CodedTerm("C49677", "DIABP"),
        CodedTerm("C49678", "PULSE"),
        CodedTerm("C49680", "TEMP"),
        CodedTerm("C49679", "RESP"),
        CodedTerm("C49675", "HEIGHT"),
        CodedTerm("C49674", "WEIGHT"),
        CodedTerm("C49673", "BMI"),
        CodedTerm("C49672", "BSA"),
        CodedTerm("C96641", "OXYSAT"),
    ]
)

VSTEST = Codelist(
    code="C67153",
    name="Vital Signs Test Name",
    extensible=True,
    terms=[
        CodedTerm("C49676", "Systolic Blood Pressure"),
        CodedTerm("C49677", "Diastolic Blood Pressure"),
        CodedTerm("C49678", "Pulse Rate"),
        CodedTerm("C49680", "Temperature"),
        CodedTerm("C49679", "Respiratory Rate"),
        CodedTerm("C49675", "Height"),
        CodedTerm("C49674", "Weight"),
        CodedTerm("C49673", "Body Mass Index"),
        CodedTerm("C49672", "Body Surface Area"),
        CodedTerm("C96641", "Oxygen Saturation"),
    ]
)

VSPOS = Codelist(
    code="C71148",
    name="Position",
    extensible=False,
    terms=[
        CodedTerm("C62167", "SITTING"),
        CodedTerm("C62166", "STANDING"),
        CodedTerm("C62165", "SUPINE"),
    ]
)

# =============================================================================
# LABORATORY TEST CODELISTS
# =============================================================================

LBCAT = Codelist(
    code="C67154",
    name="Laboratory Test Category",
    extensible=True,
    terms=[
        CodedTerm("C25554", "CHEMISTRY"),
        CodedTerm("C25723", "HEMATOLOGY"),
        CodedTerm("C49666", "URINALYSIS"),
        CodedTerm("C49665", "COAGULATION"),
        CodedTerm("C49667", "IMMUNOLOGY"),
        CodedTerm("C49668", "MICROBIOLOGY"),
    ]
)

# Common lab tests (extensible - sponsors add many more)
LBTESTCD = Codelist(
    code="C65047",
    name="Laboratory Test Code",
    extensible=True,
    terms=[
        # Chemistry
        CodedTerm("C64547", "ALT"),
        CodedTerm("C64568", "AST"),
        CodedTerm("C64463", "ALP"),
        CodedTerm("C64848", "BILI"),
        CodedTerm("C64849", "TBILI"),
        CodedTerm("C64411", "ALB"),
        CodedTerm("C64849", "CREAT"),
        CodedTerm("C64848", "BUN"),
        CodedTerm("C64850", "GLUC"),
        CodedTerm("C64851", "SODIUM"),
        CodedTerm("C64852", "POTASSIUM"),
        CodedTerm("C64853", "CHLOR"),
        CodedTerm("C64854", "CALCIUM"),
        CodedTerm("C64855", "PHOS"),
        CodedTerm("C64856", "CHOL"),
        CodedTerm("C64857", "TRIG"),
        CodedTerm("C64858", "HDL"),
        CodedTerm("C64859", "LDL"),
        # Hematology
        CodedTerm("C64596", "HGB"),
        CodedTerm("C64597", "HCT"),
        CodedTerm("C64598", "RBC"),
        CodedTerm("C64599", "WBC"),
        CodedTerm("C64600", "PLAT"),
        CodedTerm("C64601", "NEUT"),
        CodedTerm("C64602", "LYMPH"),
        CodedTerm("C64603", "MONO"),
        CodedTerm("C64604", "EOS"),
        CodedTerm("C64605", "BASO"),
        # Coagulation
        CodedTerm("C64606", "PT"),
        CodedTerm("C64607", "INR"),
        CodedTerm("C64608", "APTT"),
    ]
)

# =============================================================================
# UNIT CODELISTS
# =============================================================================

UNIT = Codelist(
    code="C71620",
    name="Unit",
    extensible=True,
    terms=[
        # Common units
        CodedTerm("C28253", "kg"),
        CodedTerm("C28252", "g"),
        CodedTerm("C28254", "mg"),
        CodedTerm("C48155", "ug"),
        CodedTerm("C48508", "cm"),
        CodedTerm("C49668", "m"),
        CodedTerm("C49670", "in"),
        CodedTerm("C49671", "ft"),
        CodedTerm("C42559", "L"),
        CodedTerm("C28254", "mL"),
        CodedTerm("C64822", "uL"),
        CodedTerm("C42554", "mmHg"),
        CodedTerm("C42569", "beats/min"),
        CodedTerm("C42574", "breaths/min"),
        CodedTerm("C42577", "C"),
        CodedTerm("C42576", "F"),
        CodedTerm("C64798", "%"),
        CodedTerm("C48570", "kg/m2"),
        CodedTerm("C48571", "m2"),
        # Lab units
        CodedTerm("C67327", "U/L"),
        CodedTerm("C67015", "g/dL"),
        CodedTerm("C64783", "mg/dL"),
        CodedTerm("C48572", "mmol/L"),
        CodedTerm("C48573", "umol/L"),
        CodedTerm("C64784", "mEq/L"),
        CodedTerm("C67309", "10^9/L"),
        CodedTerm("C67310", "10^12/L"),
        CodedTerm("C67311", "10^6/uL"),
        CodedTerm("C67316", "sec"),
    ]
)

# =============================================================================
# YES/NO CODELISTS (used in multiple domains)
# =============================================================================

NY = Codelist(
    code="C66742",
    name="No Yes Response",
    extensible=False,
    terms=[
        CodedTerm("C49488", "N"),
        CodedTerm("C49487", "Y"),
    ]
)

NYU = Codelist(
    code="C66743",
    name="No Yes Unknown Response",
    extensible=False,
    terms=[
        CodedTerm("C49488", "N"),
        CodedTerm("C49487", "Y"),
        CodedTerm("C17998", "U"),
    ]
)

# =============================================================================
# TRIAL DESIGN CODELISTS
# =============================================================================

EPOCH = Codelist(
    code="C99073",
    name="Epoch",
    extensible=True,
    terms=[
        CodedTerm("C48262", "SCREENING"),
        CodedTerm("C98778", "RUN-IN"),
        CodedTerm("C101526", "TREATMENT"),
        CodedTerm("C99158", "FOLLOW-UP"),
        CodedTerm("C101849", "WASHOUT"),
    ]
)

TBLIND = Codelist(
    code="C99074",
    name="Trial Blinding Schema",
    extensible=False,
    terms=[
        CodedTerm("C15228", "DOUBLE BLIND"),
        CodedTerm("C15227", "SINGLE BLIND"),
        CodedTerm("C49666", "OPEN LABEL"),
    ]
)

TCNTRL = Codelist(
    code="C99075",
    name="Control Type",
    extensible=True,
    terms=[
        CodedTerm("C49648", "PLACEBO"),
        CodedTerm("C49649", "ACTIVE"),
        CodedTerm("C49650", "DOSE COMPARISON"),
        CodedTerm("C49651", "HISTORICAL"),
        CodedTerm("C48660", "UNCONTROLLED"),
    ]
)

INTMODEL = Codelist(
    code="C99076",
    name="Intervention Model",
    extensible=False,
    terms=[
        CodedTerm("C82639", "PARALLEL"),
        CodedTerm("C82638", "CROSSOVER"),
        CodedTerm("C82637", "FACTORIAL"),
        CodedTerm("C82640", "SINGLE GROUP"),
    ]
)

# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def get_codelist(name: str) -> Optional[Codelist]:
    """Get a codelist by name."""
    codelists = {
        'SEX': SEX,
        'ETHNIC': ETHNIC,
        'RACE': RACE,
        'AGEU': AGEU,
        'COUNTRY': COUNTRY,
        'AESEV': AESEV,
        'AESER': AESER,
        'AEREL': AEREL,
        'AEOUT': AEOUT,
        'AEACN': AEACN,
        'DSDECOD': DSDECOD,
        'DSCAT': DSCAT,
        'EXROUTE': EXROUTE,
        'EXDOSFRM': EXDOSFRM,
        'EXDOSFRQ': EXDOSFRQ,
        'VSTESTCD': VSTESTCD,
        'VSTEST': VSTEST,
        'VSPOS': VSPOS,
        'LBCAT': LBCAT,
        'LBTESTCD': LBTESTCD,
        'UNIT': UNIT,
        'NY': NY,
        'NYU': NYU,
        'EPOCH': EPOCH,
        'TBLIND': TBLIND,
        'TCNTRL': TCNTRL,
        'INTMODEL': INTMODEL,
    }
    return codelists.get(name.upper())


def get_submission_values(codelist_name: str) -> List[str]:
    """Get all submission values for a codelist."""
    cl = get_codelist(codelist_name)
    if cl:
        return [term.value for term in cl.terms]
    return []


def get_code_for_value(codelist_name: str, value: str) -> Optional[str]:
    """Get the NCI C-code for a submission value."""
    cl = get_codelist(codelist_name)
    if cl:
        for term in cl.terms:
            if term.value.upper() == value.upper():
                return term.code
    return None


def is_valid_value(codelist_name: str, value: str) -> bool:
    """Check if a value is valid for a codelist."""
    values = get_submission_values(codelist_name)
    return value.upper() in [v.upper() for v in values]


def validate_term(codelist_name: str, value: str) -> Dict[str, any]:
    """Validate a term and return details."""
    cl = get_codelist(codelist_name)
    if not cl:
        return {
            'valid': False,
            'error': f"Unknown codelist: {codelist_name}",
            'codelist': None,
        }
    
    for term in cl.terms:
        if term.value.upper() == value.upper():
            return {
                'valid': True,
                'codelist': cl.name,
                'codelist_code': cl.code,
                'term_code': term.code,
                'submission_value': term.value,
                'extensible': cl.extensible,
            }
    
    if cl.extensible:
        return {
            'valid': True,  # Extensible codelists allow sponsor-defined values
            'codelist': cl.name,
            'codelist_code': cl.code,
            'term_code': None,  # Sponsor-defined
            'submission_value': value,
            'extensible': True,
            'warning': f"Value '{value}' not in standard terminology (extensible codelist)",
        }
    
    return {
        'valid': False,
        'error': f"Invalid value '{value}' for codelist {codelist_name}",
        'codelist': cl.name,
        'allowed_values': get_submission_values(codelist_name),
    }


# =============================================================================
# TERMINOLOGY VERSION INFO
# =============================================================================

TERMINOLOGY_VERSION = "2023-12-15"
TERMINOLOGY_SOURCE = "CDISC SDTM Controlled Terminology (NCI EVS)"
