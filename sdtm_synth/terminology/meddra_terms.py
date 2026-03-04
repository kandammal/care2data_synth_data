"""
MedDRA Term Library for Synthetic SDTM Generation — Phase 2 §3.1

Provides PT-level terms with full hierarchy columns:
  AEDECOD (PT), AEPTCD, AEHLT, AEHLTCD, AEHLGT, AEHLGTCD, AESOC, AESOCCD

Terms are drawn from the project knowledge MedDRA hierarchy templates
plus additional indication-specific terms for each protocol.
"""

from __future__ import annotations
from dataclasses import dataclass
from typing import Dict, List, Optional


@dataclass(frozen=True)
class MedDRATerm:
    """Full MedDRA hierarchy for a single Preferred Term."""
    pt_name: str        # AEDECOD
    pt_code: int        # AEPTCD
    hlt_name: str       # AEHLT
    hlt_code: int       # AEHLTCD
    hlgt_name: str = "" # AEHLGT (optional for now)
    hlgt_code: int = 0  # AEHLGTCD
    soc_name: str = ""  # AESOC / AEBODSYS
    soc_code: int = 0   # AESOCCD / AEBDSYCD
    can_be_fatal: bool = False
    weight: float = 1.0  # relative frequency weight


# ─── Core MedDRA Terms (from project knowledge + extended) ──────────────────
# These match the meddra_pt_hierarchy_templates_only.pdf exactly where available

CORE_MEDDRA_TERMS: List[MedDRATerm] = [
    # Gastrointestinal disorders
    MedDRATerm("Abdominal pain", 10000081, "Gastrointestinal and abdominal pains (excl oral and throat)", 10017926,
              "Gastrointestinal signs and symptoms", 10017999, "Gastrointestinal disorders", 10017947, weight=0.08),
    MedDRATerm("Diarrhoea", 10012735, "Diarrhoea (excl infective)", 10012736,
              "Gastrointestinal motility and defaecation conditions", 10017983, "Gastrointestinal disorders", 10017947, weight=0.10),
    MedDRATerm("Nausea", 10028813, "Nausea and vomiting symptoms", 10028817,
              "Gastrointestinal signs and symptoms", 10017999, "Gastrointestinal disorders", 10017947, weight=0.15),
    MedDRATerm("Vomiting", 10047700, "Nausea and vomiting symptoms", 10028817,
              "Gastrointestinal signs and symptoms", 10017999, "Gastrointestinal disorders", 10017947, weight=0.06),
    MedDRATerm("Constipation", 10010774, "Gastrointestinal motility and defaecation conditions NEC", 10067985,
              "Gastrointestinal motility and defaecation conditions", 10017983, "Gastrointestinal disorders", 10017947, weight=0.05),

    # Nervous system disorders
    MedDRATerm("Headache", 10019211, "Headaches NEC", 10019233,
              "Headaches", 10019231, "Nervous system disorders", 10029205, weight=0.20),
    MedDRATerm("Dizziness", 10013573, "Dizziness and vertigo symptoms", 10049370,
              "Neurological signs and symptoms NEC", 10049372, "Nervous system disorders", 10029205, weight=0.08),
    MedDRATerm("Somnolence", 10041349, "Disturbances in consciousness NEC", 10013396,
              "Neurological signs and symptoms NEC", 10049372, "Nervous system disorders", 10029205, weight=0.04),

    # General disorders and admin site conditions
    MedDRATerm("Fatigue", 10016256, "Asthenic conditions", 10003550,
              "General system disorders NEC", 10060892, "General disorders and administration site conditions", 10018065, weight=0.15),
    MedDRATerm("Pyrexia", 10037660, "Body temperature conditions", 10005906,
              "General system disorders NEC", 10060892, "General disorders and administration site conditions", 10018065, weight=0.04),

    # Infections and infestations
    MedDRATerm("Nasopharyngitis", 10028810, "Upper respiratory tract infections", 10046309,
              "Upper respiratory tract infections", 10046309, "Infections and infestations", 10021881, weight=0.10),
    MedDRATerm("Upper respiratory tract infection", 10046306, "Upper respiratory tract infections", 10046309,
              "Upper respiratory tract infections", 10046309, "Infections and infestations", 10021881, weight=0.06),

    # Musculoskeletal and connective tissue disorders
    MedDRATerm("Arthralgia", 10003239, "Joint related signs and symptoms", 10023226,
              "Joint disorders", 10023215, "Musculoskeletal and connective tissue disorders", 10028395, weight=0.06),
    MedDRATerm("Back pain", 10003988, "Spinal column and cord signs and symptoms", 10041367,
              "Musculoskeletal and connective tissue signs and symptoms NEC", 10063536, "Musculoskeletal and connective tissue disorders", 10028395, weight=0.05),
    MedDRATerm("Myalgia", 10028411, "Muscle pains", 10028417,
              "Musculoskeletal and connective tissue signs and symptoms NEC", 10063536, "Musculoskeletal and connective tissue disorders", 10028395, weight=0.04),

    # Skin and subcutaneous tissue disorders
    MedDRATerm("Rash", 10037844, "Rashes, eruptions and exanthems NEC", 10052566,
              "Epidermal and dermal conditions", 10014966, "Skin and subcutaneous tissue disorders", 10040785, weight=0.05),
    MedDRATerm("Pruritus", 10037087, "Pruritus NEC", 10037089,
              "Epidermal and dermal conditions", 10014966, "Skin and subcutaneous tissue disorders", 10040785, weight=0.03),

    # Vascular disorders
    MedDRATerm("Hypertension", 10020772, "Vascular hypertensive disorders NEC", 10020774,
              "Vascular hypertensive disorders", 10047560, "Vascular disorders", 10047065, weight=0.04),

    # Psychiatric disorders
    MedDRATerm("Insomnia", 10022437, "Sleep disorders and disturbances", 10040984,
              "Sleep disturbances (incl subtypes)", 10040983, "Psychiatric disorders", 10037175, weight=0.05),

    # Blood and lymphatic system disorders
    MedDRATerm("Lymphopenia", 10025327, "Leukopenias NEC", 10024385,
              "Leucocyte disorders", 10049163, "Blood and lymphatic system disorders", 10005329, weight=0.02),

    # Investigations
    MedDRATerm("Alanine aminotransferase increased", 10001551, "Liver function analyses", 10024689,
              "Hepatobiliary investigations", 10019843, "Investigations", 10022891, weight=0.03),

    # Immune system disorders
    MedDRATerm("Cytokine release syndrome", 10052015, "Immune and associated conditions NEC", 10027682,
              "Autoimmune disorders", 10003815, "Immune system disorders", 10021428, weight=0.01, can_be_fatal=True),

    # Cardiac disorders (serious/fatal)
    MedDRATerm("Myocardial infarction", 10028596, "Ischaemic coronary artery disorders", 10061218,
              "Coronary artery disorders", 10011078, "Cardiac disorders", 10007541, weight=0.005, can_be_fatal=True),

    # Infections (serious/fatal)
    MedDRATerm("Pneumonia", 10035664, "Lower respiratory and lung infections", 10024968,
              "Infections NEC", 10021902, "Infections and infestations", 10021881, weight=0.01, can_be_fatal=True),
    MedDRATerm("Sepsis", 10040047, "Sepsis, bacteraemia, viraemia and fungaemia NEC", 10040062,
              "Infections NEC", 10021902, "Infections and infestations", 10021881, weight=0.003, can_be_fatal=True),
]


# ─── Indication-Specific Term Libraries ─────────────────────────────────────

# BDA / Asthma / EIB - Prot_008
BDA_AE_TERMS: List[MedDRATerm] = [
    MedDRATerm("Headache", 10019211, "Headaches NEC", 10019233,
              "Headaches", 10019231, "Nervous system disorders", 10029205, weight=0.15),
    MedDRATerm("Oropharyngeal pain", 10068319, "Oral soft tissue conditions NEC", 10068876,
              "Oral soft tissue conditions", 10061998, "Gastrointestinal disorders", 10017947, weight=0.10),
    MedDRATerm("Dysphonia", 10013952, "Speech and language abnormalities", 10041366,
              "Neurological signs and symptoms NEC", 10049372, "Nervous system disorders", 10029205, weight=0.08),
    MedDRATerm("Oral candidiasis", 10030963, "Oral fungal infections", 10030967,
              "Infections NEC", 10021902, "Infections and infestations", 10021881, weight=0.06),
    MedDRATerm("Cough", 10011224, "Coughing and associated symptoms", 10011228,
              "Respiratory tract signs and symptoms", 10038734, "Respiratory, thoracic and mediastinal disorders", 10038738, weight=0.12),
    MedDRATerm("Tremor", 10044565, "Tremor (excl congenital)", 10044570,
              "Movement disorders", 10027653, "Nervous system disorders", 10029205, weight=0.08),
    MedDRATerm("Nausea", 10028813, "Nausea and vomiting symptoms", 10028817,
              "Gastrointestinal signs and symptoms", 10017999, "Gastrointestinal disorders", 10017947, weight=0.07),
    MedDRATerm("Tachycardia", 10043071, "Rate and rhythm disorders NEC", 10037908,
              "Cardiac arrhythmias", 10007518, "Cardiac disorders", 10007541, weight=0.05),
    MedDRATerm("Dizziness", 10013573, "Dizziness and vertigo symptoms", 10049370,
              "Neurological signs and symptoms NEC", 10049372, "Nervous system disorders", 10029205, weight=0.06),
    MedDRATerm("Nasopharyngitis", 10028810, "Upper respiratory tract infections", 10046309,
              "Upper respiratory tract infections", 10046309, "Infections and infestations", 10021881, weight=0.08),
]

# USL261 / Seizure Clusters / Epilepsy - Prot_009
USL261_AE_TERMS: List[MedDRATerm] = [
    MedDRATerm("Somnolence", 10041349, "Disturbances in consciousness NEC", 10013396,
              "Neurological signs and symptoms NEC", 10049372, "Nervous system disorders", 10029205, weight=0.20),
    MedDRATerm("Headache", 10019211, "Headaches NEC", 10019233,
              "Headaches", 10019231, "Nervous system disorders", 10029205, weight=0.15),
    MedDRATerm("Nasal discomfort", 10028735, "Nasal disorders NEC", 10028749,
              "Respiratory tract signs and symptoms", 10038734, "Respiratory, thoracic and mediastinal disorders", 10038738, weight=0.12),
    MedDRATerm("Dysgeusia", 10013911, "Neurological signs and symptoms NEC", 10049372,
              "Neurological signs and symptoms NEC", 10049372, "Nervous system disorders", 10029205, weight=0.10),
    MedDRATerm("Lacrimation increased", 10023644, "Ocular disorders NEC", 10061519,
              "Ocular disorders NEC", 10061519, "Eye disorders", 10015919, weight=0.08),
    MedDRATerm("Rhinorrhoea", 10039101, "Nasal disorders NEC", 10028749,
              "Respiratory tract signs and symptoms", 10038734, "Respiratory, thoracic and mediastinal disorders", 10038738, weight=0.07),
    MedDRATerm("Fatigue", 10016256, "Asthenic conditions", 10003550,
              "General system disorders NEC", 10060892, "General disorders and administration site conditions", 10018065, weight=0.08),
    MedDRATerm("Dizziness", 10013573, "Dizziness and vertigo symptoms", 10049370,
              "Neurological signs and symptoms NEC", 10049372, "Nervous system disorders", 10029205, weight=0.06),
    MedDRATerm("Nausea", 10028813, "Nausea and vomiting symptoms", 10028817,
              "Gastrointestinal signs and symptoms", 10017999, "Gastrointestinal disorders", 10017947, weight=0.05),
    MedDRATerm("Convulsion", 10010904, "Seizures and seizure disorders NEC", 10039911,
              "Seizures (incl subtypes)", 10039906, "Nervous system disorders", 10029205, weight=0.03),
]

# KONFIDENT / HAE / KVD900 - Prot_010
KONFIDENT_AE_TERMS: List[MedDRATerm] = [
    MedDRATerm("Headache", 10019211, "Headaches NEC", 10019233,
              "Headaches", 10019231, "Nervous system disorders", 10029205, weight=0.15),
    MedDRATerm("Nausea", 10028813, "Nausea and vomiting symptoms", 10028817,
              "Gastrointestinal signs and symptoms", 10017999, "Gastrointestinal disorders", 10017947, weight=0.12),
    MedDRATerm("Fatigue", 10016256, "Asthenic conditions", 10003550,
              "General system disorders NEC", 10060892, "General disorders and administration site conditions", 10018065, weight=0.10),
    MedDRATerm("Diarrhoea", 10012735, "Diarrhoea (excl infective)", 10012736,
              "Gastrointestinal motility and defaecation conditions", 10017983, "Gastrointestinal disorders", 10017947, weight=0.08),
    MedDRATerm("Abdominal pain", 10000081, "Gastrointestinal and abdominal pains (excl oral and throat)", 10017926,
              "Gastrointestinal signs and symptoms", 10017999, "Gastrointestinal disorders", 10017947, weight=0.08),
    MedDRATerm("Dizziness", 10013573, "Dizziness and vertigo symptoms", 10049370,
              "Neurological signs and symptoms NEC", 10049372, "Nervous system disorders", 10029205, weight=0.06),
    MedDRATerm("Injection site reaction", 10022095, "Injection site reactions", 10022096,
              "Administration site reactions", 10000860, "General disorders and administration site conditions", 10018065, weight=0.05),
    MedDRATerm("Rash", 10037844, "Rashes, eruptions and exanthems NEC", 10052566,
              "Epidermal and dermal conditions", 10014966, "Skin and subcutaneous tissue disorders", 10040785, weight=0.04),
    MedDRATerm("Nasopharyngitis", 10028810, "Upper respiratory tract infections", 10046309,
              "Upper respiratory tract infections", 10046309, "Infections and infestations", 10021881, weight=0.06),
    MedDRATerm("Angioedema", 10002424, "Angioedemas", 10002425,
              "Angioedema and urticaria", 10059826, "Skin and subcutaneous tissue disorders", 10040785, weight=0.03),
]


# ─── Protocol → Term Library Mapping ─────────────────────────────────────────
PROTOCOL_TERM_LIBRARIES: Dict[str, List[MedDRATerm]] = {
    'bda': BDA_AE_TERMS,
    'usl261': USL261_AE_TERMS,
    'konfident': KONFIDENT_AE_TERMS,
}


def get_term_library(protocol_key: Optional[str] = None) -> List[MedDRATerm]:
    """Get the MedDRA term library for a protocol or fall back to core terms."""
    if protocol_key and protocol_key.lower() in PROTOCOL_TERM_LIBRARIES:
        return PROTOCOL_TERM_LIBRARIES[protocol_key.lower()]
    return CORE_MEDDRA_TERMS


def meddra_term_to_dict(term: MedDRATerm) -> Dict:
    """Convert MedDRATerm to flat dict for AE generation compatibility."""
    return {
        'term': term.pt_name.upper(),
        'decoded': term.pt_name,
        'bodsys': term.soc_name,
        'weight': term.weight,
        'can_be_fatal': term.can_be_fatal,
        # Full MedDRA hierarchy
        'pt_code': term.pt_code,
        'hlt_name': term.hlt_name,
        'hlt_code': term.hlt_code,
        'hlgt_name': term.hlgt_name,
        'hlgt_code': term.hlgt_code,
        'soc_name': term.soc_name,
        'soc_code': term.soc_code,
    }


# ─── Additional Indication-Specific MedDRA Terms ────────────────────────────
# These extend the core library with terms commonly used in specific indications
# to improve MedDRA hierarchy coverage for all 9 protocols.

INDICATION_MEDDRA_TERMS: List[MedDRATerm] = [
    # Gastrointestinal / UC
    MedDRATerm("Ulcerative colitis", 10045342, "Colitis ulcerative and ischaemic", 10009897,
              "Gastrointestinal inflammatory conditions", 10017985, "Gastrointestinal disorders", 10017947, weight=0.01),
    MedDRATerm("Rectal haemorrhage", 10038063, "Gastrointestinal haemorrhages NEC", 10017936,
              "Gastrointestinal haemorrhages", 10017932, "Gastrointestinal disorders", 10017947, weight=0.01),

    # Blood / Haematology
    MedDRATerm("Anaemia", 10002034, "Anaemias NEC", 10060924,
              "Anaemias nonhaemolytic and marrow depression", 10002057, "Blood and lymphatic system disorders", 10005329, weight=0.01),
    MedDRATerm("Haemolysis", 10018867, "Haemolytic disorders and related conditions NEC", 10068746,
              "Haemolytic disorders and related conditions", 10056249, "Blood and lymphatic system disorders", 10005329, weight=0.01),
    MedDRATerm("Neutropenia", 10029354, "Neutropenias", 10029358,
              "Leucocyte disorders", 10049163, "Blood and lymphatic system disorders", 10005329, weight=0.01),

    # Injection site / Administration site
    MedDRATerm("Injection site reaction", 10022095, "Injection site reactions", 10022096,
              "Administration site reactions", 10000860, "General disorders and administration site conditions", 10018065, weight=0.01),
    MedDRATerm("Injection site pain", 10022086, "Injection site reactions", 10022096,
              "Administration site reactions", 10000860, "General disorders and administration site conditions", 10018065, weight=0.01),

    # Endocrine / Metabolic
    MedDRATerm("Hypoglycaemia", 10020993, "Hypoglycaemic conditions NEC", 10021007,
              "Glucose metabolism disorders (incl diabetes mellitus)", 10018429, "Metabolism and nutrition disorders", 10027433, weight=0.01),
    MedDRATerm("Weight decreased", 10047895, "Body weight issues", 10005893,
              "Physical examination findings and perturbation", 10059021, "Investigations", 10022891, weight=0.01),

    # Dermatological
    MedDRATerm("Dermatitis", 10012431, "Dermatitis and eczema", 10012432,
              "Epidermal and dermal conditions", 10014966, "Skin and subcutaneous tissue disorders", 10040785, weight=0.01),

    # Respiratory
    MedDRATerm("Cough", 10011224, "Coughing and associated symptoms", 10011228,
              "Respiratory tract signs and symptoms", 10038734, "Respiratory, thoracic and mediastinal disorders", 10038738, weight=0.01),
    MedDRATerm("Dyspnoea", 10013968, "Breathing abnormalities", 10006486,
              "Respiratory tract signs and symptoms", 10038734, "Respiratory, thoracic and mediastinal disorders", 10038738, weight=0.01),

    # Renal
    MedDRATerm("Blood creatinine increased", 10005483, "Renal function analyses", 10038432,
              "Renal and urinary tract investigations and urinalyses", 10062225, "Investigations", 10022891, weight=0.01),

    # Hepatic
    MedDRATerm("Hepatic enzyme increased", 10060795, "Liver function analyses", 10024689,
              "Hepatobiliary investigations", 10019843, "Investigations", 10022891, weight=0.01),

    # Infusion-related
    MedDRATerm("Infusion related reaction", 10051792, "Immune and associated conditions NEC", 10027682,
              "Autoimmune disorders", 10003815, "Immune system disorders", 10021428, weight=0.01),

    # Vascular / Circulatory
    MedDRATerm("Acrocyanosis", 10000545, "Peripheral vascular disorders NEC", 10034580,
              "Vascular disorders NEC", 10068863, "Vascular disorders", 10047065, weight=0.01),
]

# Extend the core library with indication-specific terms (for lookup enrichment)
_ALL_MEDDRA_TERMS = CORE_MEDDRA_TERMS + INDICATION_MEDDRA_TERMS

def get_all_meddra_terms() -> List[MedDRATerm]:
    """Get complete MedDRA term library including indication-specific extensions."""
    return _ALL_MEDDRA_TERMS
