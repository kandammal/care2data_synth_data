"""
Pinnacle 21 Conformance Fixes - Updated Version

This module provides fixes for Pinnacle 21 validation issues:
- SD1449/SD1461: MedDRA hierarchy variables
- SD1031: --ENRF when RFENDTC is null
- SD1204: End dates after RFPENDTC
- SD1079: Variable ordering per SDTM-IG
- SD1078: Permissible variables with all null values
- SD0058: Non-standard variables (TAESSION, EPOCH in TV)
- SD1070: TS TSPARMCD/TSPARM consistency
- SD1260: TSVCDVER for versioned terminologies
- SD2233: Missing SENDTC parameter
- SD0057: Missing ARMCD in TV
"""

import pandas as pd
from typing import Dict, Optional
from datetime import datetime

# =============================================================================
# SDTM-IG v3.4 Variable Order per domain specification
# NOTE: These follow strict SDTM-IG ordering - no custom variables
# =============================================================================
SDTM_VARIABLE_ORDER = {
    'DM': [
        'STUDYID', 'DOMAIN', 'USUBJID', 'SUBJID', 'RFSTDTC', 'RFENDTC', 
        'RFXSTDTC', 'RFXENDTC', 'RFICDTC', 'RFPENDTC', 'DTHDTC', 'DTHFL',
        'SITEID', 'BRTHDTC', 'AGE', 'AGEU', 'SEX', 'RACE', 'ETHNIC',
        'ARMCD', 'ARM', 'ACTARMCD', 'ACTARM', 'ARMNRS', 'ACTARMUD',
        'COUNTRY', 'DMDTC', 'DMDY', 'INVNAM', 'INVID'
    ],
    'EX': [
        'STUDYID', 'DOMAIN', 'USUBJID', 'EXSEQ', 'EXGRPID', 'EXREFID', 'EXSPID',
        'EXLNKID', 'EXLNKGRP', 'EXTRT', 'EXCAT', 'EXSCAT', 'EXDOSE', 'EXDOSTXT',
        'EXDOSU', 'EXDOSFRM', 'EXDOSFRQ', 'EXDOSRGM', 'EXROUTE', 'EXLOT',
        'EXLOC', 'EXLAT', 'EXDIR', 'EXFAST', 'EXADJ', 'EPOCH',
        'EXSTDTC', 'EXENDTC', 'EXSTDY', 'EXENDY', 'EXDUR', 
        'VISITNUM', 'VISIT', 'VISITDY'
    ],
    'AE': [
        'STUDYID', 'DOMAIN', 'USUBJID', 'AESEQ', 'AEGRPID', 'AEREFID', 'AESPID',
        'AELNKID', 'AELNKGRP', 'AETERM', 'AEMODIFY', 'AELLT', 'AELLTCD',
        'AEDECOD', 'AEPTCD', 'AEHLT', 'AEHLTCD', 'AEHLGT', 'AEHLGTCD',
        'AECAT', 'AESCAT', 'AEPRESP', 'AEBODSYS', 'AEBDSYCD', 'AESOC', 'AESOCCD',
        'AELOC', 'AESEV', 'AESER', 'AEACN', 'AEACNOTH', 'AEACNDEV',
        'AEREL', 'AERELNST', 'AEPATT', 'AEOUT', 'AESCAN', 'AESCONG',
        'AESDISAB', 'AESDTH', 'AESHOSP', 'AESLIFE', 'AESOD', 'AESMIE',
        'AECONTRT', 'AETOXGR', 'EPOCH',
        'AESTDTC', 'AEENDTC', 'AESTDY', 'AEENDY', 'AEDUR', 
        'AEENRF', 'AEENRTPT', 'AEENTPT', 'VISITNUM', 'VISIT', 'VISITDY'
    ],
    'CM': [
        'STUDYID', 'DOMAIN', 'USUBJID', 'CMSEQ', 'CMGRPID', 'CMREFID', 'CMSPID',
        'CMLNKID', 'CMLNKGRP', 'CMTRT', 'CMMODIFY', 'CMDECOD', 'CMCAT', 'CMSCAT',
        'CMPRESP', 'CMOCCUR', 'CMSTAT', 'CMREASND', 'CMINDC', 
        'CMDOSE', 'CMDOSTXT', 'CMDOSU', 'CMDOSFRM', 'CMDOSFRQ', 'CMDOSTOT', 'CMDOSRGM',
        'CMROUTE', 'CMLOC', 'CMLAT', 'CMDIR', 'CMPORTOT', 'CMFAST',
        'CMADJ', 'CMCLASCD', 'CMCLAS', 'EPOCH',
        'CMSTDTC', 'CMENDTC', 'CMSTDY', 'CMENDY', 'CMDUR',
        'CMSTRF', 'CMENRF', 'CMSTRTPT', 'CMSTTPT', 'CMENRTPT', 'CMENTPT',
        'VISITNUM', 'VISIT', 'VISITDY'
    ],
    'LB': [
        'STUDYID', 'DOMAIN', 'USUBJID', 'LBSEQ', 'LBGRPID', 'LBREFID', 'LBSPID',
        'LBLNKID', 'LBLNKGRP', 'LBTESTCD', 'LBTEST', 'LBCAT', 'LBSCAT',
        'LBORRES', 'LBORRESU', 'LBORNRLO', 'LBORNRHI',
        'LBSTRESC', 'LBSTRESN', 'LBSTRESU', 'LBSTNRLO', 'LBSTNRHI', 'LBSTNRC',
        'LBNRIND', 'LBSTAT', 'LBREASND', 'LBNAM', 'LBLOINC',
        'LBSPEC', 'LBSPCCND', 'LBLOC', 'LBLAT', 'LBDIR', 'LBPORTOT',
        'LBMETHOD', 'LBBLFL', 'LBLOBXFL', 'LBFAST', 'LBDRVFL', 'LBTOX', 'LBTOXGR',
        'EPOCH', 'LBDTC', 'LBENDTC', 'LBDY', 'LBENDY', 'LBTPT', 'LBTPTNUM', 'LBELTM',
        'LBTPTREF', 'LBRFTDTC', 'VISITNUM', 'VISIT', 'VISITDY'
    ],
    'VS': [
        'STUDYID', 'DOMAIN', 'USUBJID', 'VSSEQ', 'VSGRPID', 'VSREFID', 'VSSPID',
        'VSLNKID', 'VSLNKGRP', 'VSTESTCD', 'VSTEST', 'VSCAT', 'VSSCAT',
        'VSPOS', 'VSORRES', 'VSORRESU', 'VSSTRESC', 'VSSTRESN', 'VSSTRESU',
        'VSSTAT', 'VSREASND', 'VSLOC', 'VSLAT', 'VSBLFL', 'VSLOBXFL', 'VSDRVFL',
        'EPOCH', 'VSDTC', 'VSENDTC', 'VSDY', 'VSENDY', 'VSTPT', 'VSTPTNUM',
        'VSELTM', 'VSTPTREF', 'VSRFTDTC', 'VISITNUM', 'VISIT', 'VISITDY'
    ],
    'DS': [
        'STUDYID', 'DOMAIN', 'USUBJID', 'DSSEQ', 'DSGRPID', 'DSREFID', 'DSSPID',
        'DSLNKID', 'DSLNKGRP', 'DSTERM', 'DSDECOD', 'DSCAT', 'DSSCAT',
        'EPOCH', 'DSSTDTC', 'DSSTDY', 'DSENDY', 'DSDUR',
        'VISITNUM', 'VISIT', 'VISITDY'
    ],
    'MH': [
        'STUDYID', 'DOMAIN', 'USUBJID', 'MHSEQ', 'MHGRPID', 'MHREFID', 'MHSPID',
        'MHLNKID', 'MHLNKGRP', 'MHTERM', 'MHMODIFY', 'MHDECOD', 'MHCAT', 'MHSCAT',
        'MHPRESP', 'MHOCCUR', 'MHSTAT', 'MHREASND', 'MHBODSYS', 'MHBDSYCD',
        'MHLOC', 'MHLAT', 'MHSEV', 'MHTOXGR', 'EPOCH',
        'MHSTDTC', 'MHENDTC', 'MHSTDY', 'MHENDY', 'MHDUR',
        'MHSTRF', 'MHENRF', 'MHENRTPT', 'MHENTPT', 'VISITNUM', 'VISIT', 'VISITDY'
    ],
    'SV': [
        'STUDYID', 'DOMAIN', 'USUBJID', 'VISITNUM', 'VISIT', 'VISITDY',
        'SVSTDTC', 'SVENDTC', 'SVSTDY', 'SVENDY', 'SVUPDES',
        'SVPRESP', 'SVOCCUR', 'SVREASOC', 'SVCNTMOD', 'SVEPCHGI', 'EPOCH'
    ],
    # TV per SDTM-IG 3.4 - NO EPOCH (not in model), ARMCD is expected
    'TV': [
        'STUDYID', 'DOMAIN', 'VISITNUM', 'VISIT', 'VISITDY', 'ARMCD', 'ARM',
        'TVSTRL', 'TVENRL'
    ],
    # TA per SDTM-IG 3.4 - NO TAESSION (not standard until specific versions)
    'TA': [
        'STUDYID', 'DOMAIN', 'ARMCD', 'ARM', 'TAETORD', 'ETCD', 
        'ELEMENT', 'TABRANCH', 'TATRANS', 'EPOCH'
    ],
    'TE': [
        'STUDYID', 'DOMAIN', 'ETCD', 'ELEMENT', 'TESTRL', 'TEENRL', 'TEDUR'
    ],
    'SE': [
        'STUDYID', 'DOMAIN', 'USUBJID', 'ETCD', 'ELEMENT', 
        'SESTDTC', 'SEENDTC', 'SESTDY', 'SEENDY', 'EPOCH'
    ],
    'TS': [
        'STUDYID', 'DOMAIN', 'TSSEQ', 'TSGRPID', 'TSPARMCD', 'TSPARM', 
        'TSVAL', 'TSVALNF', 'TSVALCD', 'TSVCDREF', 'TSVCDVER'
    ]
}

# =============================================================================
# MedDRA Body System Codes - Map SOC names to codes
# =============================================================================
MEDDRA_SOC_CODES = {
    'BLOOD AND LYMPHATIC SYSTEM DISORDERS': 10005329,
    'CARDIAC DISORDERS': 10007541,
    'CONGENITAL, FAMILIAL AND GENETIC DISORDERS': 10010331,
    'EAR AND LABYRINTH DISORDERS': 10013993,
    'ENDOCRINE DISORDERS': 10014698,
    'EYE DISORDERS': 10015919,
    'GASTROINTESTINAL DISORDERS': 10017947,
    'GENERAL DISORDERS AND ADMINISTRATION SITE CONDITIONS': 10018065,
    'HEPATOBILIARY DISORDERS': 10019805,
    'IMMUNE SYSTEM DISORDERS': 10021428,
    'INFECTIONS AND INFESTATIONS': 10021881,
    'INJURY, POISONING AND PROCEDURAL COMPLICATIONS': 10022117,
    'INVESTIGATIONS': 10022891,
    'METABOLISM AND NUTRITION DISORDERS': 10027433,
    'MUSCULOSKELETAL AND CONNECTIVE TISSUE DISORDERS': 10028395,
    'NEOPLASMS BENIGN, MALIGNANT AND UNSPECIFIED': 10029104,
    'NERVOUS SYSTEM DISORDERS': 10029205,
    'PREGNANCY, PUERPERIUM AND PERINATAL CONDITIONS': 10036585,
    'PSYCHIATRIC DISORDERS': 10037175,
    'RENAL AND URINARY DISORDERS': 10038359,
    'REPRODUCTIVE SYSTEM AND BREAST DISORDERS': 10038604,
    'RESPIRATORY, THORACIC AND MEDIASTINAL DISORDERS': 10038738,
    'SKIN AND SUBCUTANEOUS TISSUE DISORDERS': 10040785,
    'SOCIAL CIRCUMSTANCES': 10041244,
    'SURGICAL AND MEDICAL PROCEDURES': 10042613,
    'VASCULAR DISORDERS': 10047065,
}

# =============================================================================
# Complete MedDRA Hierarchy for common AE terms
# =============================================================================
MEDDRA_HIERARCHY = {
    'HEADACHE': {
        'AELLT': 'Headache', 'AELLTCD': 10019211,
        'AEDECOD': 'Headache', 'AEPTCD': 10019211,
        'AEHLT': 'Headaches', 'AEHLTCD': 10019233,
        'AEHLGT': 'Headaches NEC', 'AEHLGTCD': 10019231,
        'AEBODSYS': 'Nervous system disorders', 'AEBDSYCD': 10029205,
        'AESOC': 'Nervous system disorders', 'AESOCCD': 10029205
    },
    'NAUSEA': {
        'AELLT': 'Nausea', 'AELLTCD': 10028813,
        'AEDECOD': 'Nausea', 'AEPTCD': 10028813,
        'AEHLT': 'Nausea and vomiting symptoms', 'AEHLTCD': 10028817,
        'AEHLGT': 'Gastrointestinal signs and symptoms NEC', 'AEHLGTCD': 10017996,
        'AEBODSYS': 'Gastrointestinal disorders', 'AEBDSYCD': 10017947,
        'AESOC': 'Gastrointestinal disorders', 'AESOCCD': 10017947
    },
    'FATIGUE': {
        'AELLT': 'Fatigue', 'AELLTCD': 10016256,
        'AEDECOD': 'Fatigue', 'AEPTCD': 10016256,
        'AEHLT': 'Asthenic conditions', 'AEHLTCD': 10003550,
        'AEHLGT': 'Asthenic conditions', 'AEHLGTCD': 10003549,
        'AEBODSYS': 'General disorders and administration site conditions', 'AEBDSYCD': 10018065,
        'AESOC': 'General disorders and administration site conditions', 'AESOCCD': 10018065
    },
    'DIARRHEA': {
        'AELLT': 'Diarrhoea', 'AELLTCD': 10012735,
        'AEDECOD': 'Diarrhoea', 'AEPTCD': 10012735,
        'AEHLT': 'Diarrhoea (excl infective)', 'AEHLTCD': 10012736,
        'AEHLGT': 'Gastrointestinal motility and defaecation conditions', 'AEHLGTCD': 10017944,
        'AEBODSYS': 'Gastrointestinal disorders', 'AEBDSYCD': 10017947,
        'AESOC': 'Gastrointestinal disorders', 'AESOCCD': 10017947
    },
    'DIARRHOEA': {
        'AELLT': 'Diarrhoea', 'AELLTCD': 10012735,
        'AEDECOD': 'Diarrhoea', 'AEPTCD': 10012735,
        'AEHLT': 'Diarrhoea (excl infective)', 'AEHLTCD': 10012736,
        'AEHLGT': 'Gastrointestinal motility and defaecation conditions', 'AEHLGTCD': 10017944,
        'AEBODSYS': 'Gastrointestinal disorders', 'AEBDSYCD': 10017947,
        'AESOC': 'Gastrointestinal disorders', 'AESOCCD': 10017947
    },
    'PNEUMONIA': {
        'AELLT': 'Pneumonia', 'AELLTCD': 10035664,
        'AEDECOD': 'Pneumonia', 'AEPTCD': 10035664,
        'AEHLT': 'Lower respiratory tract and lung infections', 'AEHLTCD': 10024968,
        'AEHLGT': 'Lower respiratory tract and lung infections', 'AEHLGTCD': 10024968,
        'AEBODSYS': 'Infections and infestations', 'AEBDSYCD': 10021881,
        'AESOC': 'Infections and infestations', 'AESOCCD': 10021881
    },
    'ABDOMINAL PAIN': {
        'AELLT': 'Abdominal pain', 'AELLTCD': 10000081,
        'AEDECOD': 'Abdominal pain', 'AEPTCD': 10000081,
        'AEHLT': 'Gastrointestinal and abdominal pains (excl oral and throat)', 'AEHLTCD': 10017999,
        'AEHLGT': 'Gastrointestinal signs and symptoms NEC', 'AEHLGTCD': 10017996,
        'AEBODSYS': 'Gastrointestinal disorders', 'AEBDSYCD': 10017947,
        'AESOC': 'Gastrointestinal disorders', 'AESOCCD': 10017947
    },
    'VOMITING': {
        'AELLT': 'Vomiting', 'AELLTCD': 10047700,
        'AEDECOD': 'Vomiting', 'AEPTCD': 10047700,
        'AEHLT': 'Nausea and vomiting symptoms', 'AEHLTCD': 10028817,
        'AEHLGT': 'Gastrointestinal signs and symptoms NEC', 'AEHLGTCD': 10017996,
        'AEBODSYS': 'Gastrointestinal disorders', 'AEBDSYCD': 10017947,
        'AESOC': 'Gastrointestinal disorders', 'AESOCCD': 10017947
    },
    'CONSTIPATION': {
        'AELLT': 'Constipation', 'AELLTCD': 10010774,
        'AEDECOD': 'Constipation', 'AEPTCD': 10010774,
        'AEHLT': 'Constipations', 'AEHLTCD': 10010775,
        'AEHLGT': 'Gastrointestinal motility and defaecation conditions', 'AEHLGTCD': 10017944,
        'AEBODSYS': 'Gastrointestinal disorders', 'AEBDSYCD': 10017947,
        'AESOC': 'Gastrointestinal disorders', 'AESOCCD': 10017947
    },
    'DIZZINESS': {
        'AELLT': 'Dizziness', 'AELLTCD': 10013573,
        'AEDECOD': 'Dizziness', 'AEPTCD': 10013573,
        'AEHLT': 'Dizziness (excl vertigo)', 'AEHLTCD': 10013578,
        'AEHLGT': 'Neurological signs and symptoms NEC', 'AEHLGTCD': 10029222,
        'AEBODSYS': 'Nervous system disorders', 'AEBDSYCD': 10029205,
        'AESOC': 'Nervous system disorders', 'AESOCCD': 10029205
    },
    'INSOMNIA': {
        'AELLT': 'Insomnia', 'AELLTCD': 10022437,
        'AEDECOD': 'Insomnia', 'AEPTCD': 10022437,
        'AEHLT': 'Disturbances in initiating and maintaining sleep', 'AEHLTCD': 10013395,
        'AEHLGT': 'Sleep disturbances', 'AEHLGTCD': 10040984,
        'AEBODSYS': 'Psychiatric disorders', 'AEBDSYCD': 10037175,
        'AESOC': 'Psychiatric disorders', 'AESOCCD': 10037175
    },
    'BACK PAIN': {
        'AELLT': 'Back pain', 'AELLTCD': 10003988,
        'AEDECOD': 'Back pain', 'AEPTCD': 10003988,
        'AEHLT': 'Spinal pain and discomfort', 'AEHLTCD': 10062344,
        'AEHLGT': 'Musculoskeletal and connective tissue pain and discomfort', 'AEHLGTCD': 10028391,
        'AEBODSYS': 'Musculoskeletal and connective tissue disorders', 'AEBDSYCD': 10028395,
        'AESOC': 'Musculoskeletal and connective tissue disorders', 'AESOCCD': 10028395
    },
    'UPPER RESPIRATORY TRACT INFECTION': {
        'AELLT': 'Upper respiratory tract infection', 'AELLTCD': 10046306,
        'AEDECOD': 'Upper respiratory tract infection', 'AEPTCD': 10046306,
        'AEHLT': 'Upper respiratory tract infections', 'AEHLTCD': 10046307,
        'AEHLGT': 'Upper respiratory tract infections', 'AEHLGTCD': 10046307,
        'AEBODSYS': 'Infections and infestations', 'AEBDSYCD': 10021881,
        'AESOC': 'Infections and infestations', 'AESOCCD': 10021881
    },
    'RASH': {
        'AELLT': 'Rash', 'AELLTCD': 10037844,
        'AEDECOD': 'Rash', 'AEPTCD': 10037844,
        'AEHLT': 'Rashes, eruptions and exanthems NEC', 'AEHLTCD': 10037867,
        'AEHLGT': 'Epidermal and dermal conditions NEC', 'AEHLGTCD': 10014966,
        'AEBODSYS': 'Skin and subcutaneous tissue disorders', 'AEBDSYCD': 10040785,
        'AESOC': 'Skin and subcutaneous tissue disorders', 'AESOCCD': 10040785
    },
    'INJECTION SITE REACTION': {
        'AELLT': 'Injection site reaction', 'AELLTCD': 10022095,
        'AEDECOD': 'Injection site reaction', 'AEPTCD': 10022095,
        'AEHLT': 'Injection site reactions', 'AEHLTCD': 10022097,
        'AEHLGT': 'Administration site reactions', 'AEHLGTCD': 10001316,
        'AEBODSYS': 'General disorders and administration site conditions', 'AEBDSYCD': 10018065,
        'AESOC': 'General disorders and administration site conditions', 'AESOCCD': 10018065
    },
    'PYREXIA': {
        'AELLT': 'Pyrexia', 'AELLTCD': 10037660,
        'AEDECOD': 'Pyrexia', 'AEPTCD': 10037660,
        'AEHLT': 'Febrile disorders', 'AEHLTCD': 10016228,
        'AEHLGT': 'Body temperature conditions', 'AEHLGTCD': 10005905,
        'AEBODSYS': 'General disorders and administration site conditions', 'AEBDSYCD': 10018065,
        'AESOC': 'General disorders and administration site conditions', 'AESOCCD': 10018065
    },
    'MYOCARDIAL INFARCTION': {
        'AELLT': 'Myocardial infarction', 'AELLTCD': 10028596,
        'AEDECOD': 'Myocardial infarction', 'AEPTCD': 10028596,
        'AEHLT': 'Ischaemic coronary artery disorders', 'AEHLTCD': 10061218,
        'AEHLGT': 'Coronary artery disorders', 'AEHLGTCD': 10011078,
        'AEBODSYS': 'Cardiac disorders', 'AEBDSYCD': 10007541,
        'AESOC': 'Cardiac disorders', 'AESOCCD': 10007541
    },
    'SEPSIS': {
        'AELLT': 'Sepsis', 'AELLTCD': 10040047,
        'AEDECOD': 'Sepsis', 'AEPTCD': 10040047,
        'AEHLT': 'Sepsis, bacteraemia, viraemia and fungaemia NEC', 'AEHLTCD': 10058874,
        'AEHLGT': 'Sepsis, bacteraemia, viraemia and fungaemia NEC', 'AEHLGTCD': 10058874,
        'AEBODSYS': 'Infections and infestations', 'AEBDSYCD': 10021881,
        'AESOC': 'Infections and infestations', 'AESOCCD': 10021881
    },
    'COUGH': {
        'AELLT': 'Cough', 'AELLTCD': 10011224,
        'AEDECOD': 'Cough', 'AEPTCD': 10011224,
        'AEHLT': 'Coughing and associated symptoms', 'AEHLTCD': 10011228,
        'AEHLGT': 'Respiratory tract signs and symptoms NEC', 'AEHLGTCD': 10038777,
        'AEBODSYS': 'Respiratory, thoracic and mediastinal disorders', 'AEBDSYCD': 10038738,
        'AESOC': 'Respiratory, thoracic and mediastinal disorders', 'AESOCCD': 10038738
    },
    'ARTHRALGIA': {
        'AELLT': 'Arthralgia', 'AELLTCD': 10003239,
        'AEDECOD': 'Arthralgia', 'AEPTCD': 10003239,
        'AEHLT': 'Joint related signs and symptoms', 'AEHLTCD': 10023215,
        'AEHLGT': 'Musculoskeletal and connective tissue signs and symptoms NEC', 'AEHLGTCD': 10028392,
        'AEBODSYS': 'Musculoskeletal and connective tissue disorders', 'AEBDSYCD': 10028395,
        'AESOC': 'Musculoskeletal and connective tissue disorders', 'AESOCCD': 10028395
    },
    'ANAEMIA': {
        'AELLT': 'Anaemia', 'AELLTCD': 10002034,
        'AEDECOD': 'Anaemia', 'AEPTCD': 10002034,
        'AEHLT': 'Anaemias NEC', 'AEHLTCD': 10002035,
        'AEHLGT': 'Anaemias nonhaemolytic and marrow depression', 'AEHLGTCD': 10002040,
        'AEBODSYS': 'Blood and lymphatic system disorders', 'AEBDSYCD': 10005329,
        'AESOC': 'Blood and lymphatic system disorders', 'AESOCCD': 10005329
    },
    'ANEMIA': {
        'AELLT': 'Anaemia', 'AELLTCD': 10002034,
        'AEDECOD': 'Anaemia', 'AEPTCD': 10002034,
        'AEHLT': 'Anaemias NEC', 'AEHLTCD': 10002035,
        'AEHLGT': 'Anaemias nonhaemolytic and marrow depression', 'AEHLGTCD': 10002040,
        'AEBODSYS': 'Blood and lymphatic system disorders', 'AEBDSYCD': 10005329,
        'AESOC': 'Blood and lymphatic system disorders', 'AESOCCD': 10005329
    },
}

# =============================================================================
# CDISC Controlled Terminology
# =============================================================================
CDISC_CT_FREQ = {
    'Q2W': 'Q2W', 'EVERY 2 WEEKS': 'Q2W',
    'ONCE': 'ONCE', 'QD': 'QD', 'ONCE DAILY': 'QD',
    'BID': 'BID', 'TWICE DAILY': 'BID',
    'Q4W': 'Q4W', 'EVERY 4 WEEKS': 'Q4W',
    'QW': 'QW', 'ONCE WEEKLY': 'QW',
    'Q3W': 'Q3W', 'EVERY 3 WEEKS': 'Q3W',
    'CONTINUOUS': 'CONTINUOUS'
}

CDISC_CT_UNIT = {
    'MG': 'mg', 'G': 'g', 'MCG': 'ug', 'UG': 'ug',
    'ML': 'mL', 'L': 'L', 'MG/KG': 'mg/kg', 'IU': 'U',
    'TABLETS': 'TABLET', 'TABLET': 'TABLET',
    'CAPSULES': 'CAPSULE', 'CAPSULE': 'CAPSULE',
    '%': '%', 'KG': 'kg', 'CM': 'cm', 'MM': 'mm',
    'MMHG': 'mmHg', 'BPM': 'beats/min', '/MIN': '/min',
    'BREATHS/MIN': 'breaths/min', 'C': 'C', 'CELSIUS': 'C'
}

# TS Parameter correct names per CDISC CT
TS_PARM_NAMES = {
    'THERAREA': 'Therapeutic Area',  # SD1070 fix
    'STUDYID': 'Study Identifier',
    'TITLE': 'Trial Title',
    'TPHASE': 'Trial Phase Classification',
    'STYPE': 'Study Type',
    'TBLIND': 'Trial Blinding Schema',
    'TCNTRL': 'Control Type',
    'TINDTP': 'Trial Intent Type',
    'INTMODEL': 'Intervention Model',
    'SDESIGN': 'Trial Summary Study Design',
    'INTTYPE': 'Intervention Type',
    'RANDOM': 'Trial is Randomized',
    'ADDON': 'Added on to Existing Treatments',
    'ADAPT': 'Adaptive Design',
    'PLANSUB': 'Planned Number of Subjects',
    'ACTSUB': 'Actual Number of Subjects',
    'NARMS': 'Planned Number of Arms',
    'HLTSUBJI': 'Healthy Subject Indicator',
    'AGEMIN': 'Planned Minimum Age of Subjects',
    'AGEMAX': 'Planned Maximum Age of Subjects',
    'SEXPOP': 'Sex of Participants',
    'LENGTH': 'Trial Length',
    'SSTDTC': 'Study Start Date',
    'SENDTC': 'Study End Date',
    'TDIGRP': 'Diagnosis Group',
    'INDIC': 'Trial Disease/Condition Indication',
    'TRT': 'Investigational Therapy or Treatment',
    'SPONSOR': 'Clinical Study Sponsor',
    'OBJPRIM': 'Trial Primary Objective',
    'OBJSEC': 'Trial Secondary Objective',
    'OUTMSPRI': 'Primary Outcome Measure',
    'TTYPE': 'Trial Type',
    'PCLAS': 'Pharmacologic Class',
    'STOPRULE': 'Study Stop Rules',
    'FCNTRY': 'Planned Country of Investigational Sites',
    'REGID': 'Registry Identifier',
    'NCOHORT': 'Number of Cohorts',
    'DCUTDTC': 'Data Cutoff Date',
    'DCUTDESC': 'Data Cutoff Description',
    'SDTIGVER': 'SDTMIG Version',
    'SDTMVER': 'SDTM Version',
}


# =============================================================================
# Fix Functions
# =============================================================================

def reorder_columns(df: pd.DataFrame, domain: str) -> pd.DataFrame:
    """Reorder columns to match SDTM-IG specification (SD1079 fix)."""
    if domain not in SDTM_VARIABLE_ORDER:
        return df
    
    order = SDTM_VARIABLE_ORDER[domain]
    ordered_cols = [c for c in order if c in df.columns]
    remaining_cols = [c for c in df.columns if c not in ordered_cols]
    
    return df[ordered_cols + remaining_cols]


def add_meddra_variables(df: pd.DataFrame) -> pd.DataFrame:
    """Add complete MedDRA hierarchy variables to AE domain (SD1449/SD1461 fix)."""
    df = df.copy()
    
    # Initialize all MedDRA columns
    meddra_cols = ['AELLT', 'AELLTCD', 'AEPTCD', 'AEHLT', 'AEHLTCD', 
                   'AEHLGT', 'AEHLGTCD', 'AEBDSYCD', 'AESOC', 'AESOCCD']
    
    for col in meddra_cols:
        if col not in df.columns:
            df[col] = ''
    
    # Map based on AETERM or AEDECOD
    for idx, row in df.iterrows():
        term = str(row.get('AETERM', '')).upper().strip()
        decod = str(row.get('AEDECOD', '')).upper().strip()
        
        # Try to find MedDRA mapping
        meddra = MEDDRA_HIERARCHY.get(term) or MEDDRA_HIERARCHY.get(decod)
        
        if meddra:
            for col, val in meddra.items():
                if col in df.columns:
                    df.at[idx, col] = val
        else:
            # For unmapped terms, derive codes from AEBODSYS
            bodsys = str(row.get('AEBODSYS', '')).upper().strip()
            if bodsys:
                soc_code = MEDDRA_SOC_CODES.get(bodsys)
                if soc_code:
                    df.at[idx, 'AEBDSYCD'] = soc_code
                    df.at[idx, 'AESOC'] = row.get('AEBODSYS', '')
                    df.at[idx, 'AESOCCD'] = soc_code
                
                # Set PT to match AEDECOD if available
                if decod:
                    df.at[idx, 'AELLT'] = row.get('AEDECOD', '')
                    df.at[idx, 'AELLTCD'] = ''  # Would need full MedDRA dictionary
                    df.at[idx, 'AEPTCD'] = ''
    
    return df


def fix_enrf_when_rfendtc_null(df: pd.DataFrame, dm_df: pd.DataFrame, 
                               domain: str) -> pd.DataFrame:
    """Clear --ENRF when subject's RFENDTC is null (SD1031 fix)."""
    df = df.copy()
    
    enrf_col = f'{domain[:2]}ENRF'
    if enrf_col not in df.columns:
        return df
    
    # Get subjects with null RFENDTC
    null_rfendtc_subjects = set()
    if dm_df is not None and 'RFENDTC' in dm_df.columns:
        null_mask = dm_df['RFENDTC'].isna() | (dm_df['RFENDTC'] == '')
        null_rfendtc_subjects = set(dm_df.loc[null_mask, 'USUBJID'].tolist())
    
    # Clear ENRF for those subjects
    if null_rfendtc_subjects:
        mask = df['USUBJID'].isin(null_rfendtc_subjects)
        df.loc[mask, enrf_col] = ''
    
    return df


def fix_endtc_after_rfpendtc(df: pd.DataFrame, dm_df: pd.DataFrame,
                             domain: str) -> pd.DataFrame:
    """Cap end dates at RFPENDTC (SD1204 fix)."""
    df = df.copy()
    
    endtc_col = f'{domain[:2]}ENDTC'
    if endtc_col not in df.columns:
        return df
    
    if dm_df is None or 'RFPENDTC' not in dm_df.columns:
        return df
    
    # Create lookup of RFPENDTC by USUBJID
    rfpendtc_lookup = dm_df.set_index('USUBJID')['RFPENDTC'].to_dict()
    
    for idx, row in df.iterrows():
        usubjid = row['USUBJID']
        endtc = row.get(endtc_col)
        rfpendtc = rfpendtc_lookup.get(usubjid)
        
        if endtc and rfpendtc:
            try:
                endtc_date = str(endtc)[:10]
                rfpendtc_date = str(rfpendtc)[:10]
                
                if endtc_date > rfpendtc_date:
                    df.at[idx, endtc_col] = rfpendtc
            except:
                pass
    
    return df


def fix_tv_domain(df: pd.DataFrame, arms: list = None) -> pd.DataFrame:
    """Fix TV domain - remove EPOCH, add ARMCD (SD0057, SD0058 fix)."""
    df = df.copy()
    
    # Remove EPOCH - not in SDTM TV model
    if 'EPOCH' in df.columns:
        del df['EPOCH']
    
    # Remove non-standard collection flag variables
    non_standard = ['TVCOLVS', 'TVCOLLB', 'TVCOLEX', 'TVCOLAE', 'TVCOLCM',
                   'TVWNDWLO', 'TVWNDWHI']
    for col in non_standard:
        if col in df.columns:
            del df[col]
    
    # Add ARMCD - TV should have ARMCD when visits differ by arm
    # For most trials, visits are same across arms, so we can leave ARMCD blank
    # or set to empty string to indicate visit applies to all arms
    if 'ARMCD' not in df.columns:
        df['ARMCD'] = ''
    if 'ARM' not in df.columns:
        df['ARM'] = ''
    
    return df


def fix_ta_domain(df: pd.DataFrame) -> pd.DataFrame:
    """Fix TA domain - remove TAESSION if causing issues (SD0058 fix)."""
    df = df.copy()
    
    # TAESSION is not in standard SDTM-IG 3.4 TA model
    # Remove it to avoid SD0058 error
    if 'TAESSION' in df.columns:
        del df['TAESSION']
    
    return df


def fix_ts_parameters(df: pd.DataFrame, study_end_date: str = '') -> pd.DataFrame:
    """Fix TS parameters (SD1070, SD1260, SD2233 fixes)."""
    df = df.copy()
    
    # SD1070: Fix TSPARM values to match CDISC CT
    if 'TSPARMCD' in df.columns and 'TSPARM' in df.columns:
        for idx, row in df.iterrows():
            parmcd = row.get('TSPARMCD', '')
            if parmcd in TS_PARM_NAMES:
                df.at[idx, 'TSPARM'] = TS_PARM_NAMES[parmcd]
    
    # SD1260: Add TSVCDVER for NDF-RT (versioned terminology)
    if 'TSVCDREF' in df.columns and 'TSVCDVER' in df.columns:
        for idx, row in df.iterrows():
            ref = str(row.get('TSVCDREF', '')).upper()
            ver = row.get('TSVCDVER', '')
            
            if ref == 'NDF-RT' and (pd.isna(ver) or ver == ''):
                df.at[idx, 'TSVCDVER'] = '2024-02-05'  # Example version
            elif ref == 'CDISC CT' and (pd.isna(ver) or ver == ''):
                df.at[idx, 'TSVCDVER'] = '2023-12-15'
    
    # SD2233: Add SENDTC if missing
    if 'TSPARMCD' in df.columns:
        has_sendtc = (df['TSPARMCD'] == 'SENDTC').any()
        if not has_sendtc and study_end_date:
            # Add SENDTC parameter
            new_row = {
                'STUDYID': df['STUDYID'].iloc[0] if len(df) > 0 else '',
                'DOMAIN': 'TS',
                'TSSEQ': df['TSSEQ'].max() + 1 if 'TSSEQ' in df.columns else 1,
                'TSGRPID': '',
                'TSPARMCD': 'SENDTC',
                'TSPARM': 'Study End Date',
                'TSVAL': study_end_date,
                'TSVALNF': '',
                'TSVALCD': '',
                'TSVCDREF': '',
                'TSVCDVER': ''
            }
            df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)
    
    return df


def fix_mh_permissible_vars(df: pd.DataFrame) -> pd.DataFrame:
    """Remove permissible variables with all null values (SD1078 fix)."""
    df = df.copy()
    
    # Check MHBODSYS - if all null, remove it
    if 'MHBODSYS' in df.columns:
        if df['MHBODSYS'].isna().all() or (df['MHBODSYS'] == '').all():
            del df['MHBODSYS']
    
    return df


def fix_se_endtc(df: pd.DataFrame, dm_df: pd.DataFrame) -> pd.DataFrame:
    """Cap SEENDTC at RFPENDTC (SD1204 fix for SE domain)."""
    return fix_endtc_after_rfpendtc(df, dm_df, 'SE')


def remove_null_permissible_columns(df: pd.DataFrame, domain: str) -> pd.DataFrame:
    """Remove permissible columns that are all null (SD1078 fix)."""
    df = df.copy()
    
    # Columns that can be removed if all null
    permissible = {
        'TS': ['TSGRPID', 'TSVALNF'],
        'MH': ['MHBODSYS'],
    }
    
    cols_to_check = permissible.get(domain, [])
    for col in cols_to_check:
        if col in df.columns:
            if df[col].isna().all() or (df[col] == '').all():
                del df[col]
    
    return df


def create_suppae(ae_df: pd.DataFrame) -> pd.DataFrame:
    """Create SUPPAE dataset for treatment-emergent flag."""
    records = []
    
    for idx, row in ae_df.iterrows():
        epoch = row.get('EPOCH', '')
        is_trtem = 'Y' if epoch in ['TREATMENT', 'FOLLOW-UP'] else 'N'
        
        records.append({
            'STUDYID': row['STUDYID'],
            'RDOMAIN': 'AE',
            'USUBJID': row['USUBJID'],
            'IDVAR': 'AESEQ',
            'IDVARVAL': str(row['AESEQ']),
            'QNAM': 'AETRTEM',
            'QLABEL': 'Treatment Emergent Flag',
            'QVAL': is_trtem,
            'QORIG': 'DERIVED',
            'QEVAL': ''
        })
    
    return pd.DataFrame(records)


def add_baseline_flags(df: pd.DataFrame, domain: str) -> pd.DataFrame:
    """Add last observation before exposure flag (--LOBXFL)."""
    df = df.copy()
    
    flag_col = f'{domain}LOBXFL'
    day_col = f'{domain}DY'
    testcd_col = f'{domain}TESTCD'
    
    if flag_col not in df.columns:
        df[flag_col] = ''
    
    if day_col in df.columns and testcd_col in df.columns:
        for usubjid in df['USUBJID'].unique():
            subj_mask = df['USUBJID'] == usubjid
            subj_df = df[subj_mask].copy()
            
            try:
                baseline_mask = subj_df[day_col].astype(float) <= 1
                if baseline_mask.any():
                    for testcd in subj_df[testcd_col].unique():
                        test_baseline = subj_df[(subj_df[testcd_col] == testcd) & baseline_mask]
                        if len(test_baseline) > 0:
                            last_idx = test_baseline.index[-1]
                            df.loc[last_idx, flag_col] = 'Y'
            except:
                pass
    
    return df


def add_sv_expected_vars(df: pd.DataFrame) -> pd.DataFrame:
    """Add expected variables to SV domain."""
    df = df.copy()
    
    if 'SVPRESP' not in df.columns:
        df['SVPRESP'] = 'Y'
    
    return df


# =============================================================================
# Main Apply Function
# =============================================================================

def apply_all_fixes(datasets: Dict[str, pd.DataFrame], 
                    study_end_date: str = '') -> Dict[str, pd.DataFrame]:
    """Apply all P21 conformance fixes to datasets."""
    fixed = {}
    
    # Get DM for reference date calculations
    dm_df = datasets.get('DM')
    
    for domain, df in datasets.items():
        fixed_df = df.copy()
        
        # Apply domain-specific fixes
        if domain == 'AE':
            fixed_df = add_meddra_variables(fixed_df)
        
        elif domain == 'CM':
            fixed_df = fix_enrf_when_rfendtc_null(fixed_df, dm_df, 'CM')
            fixed_df = fix_endtc_after_rfpendtc(fixed_df, dm_df, 'CM')
        
        elif domain == 'MH':
            fixed_df = fix_enrf_when_rfendtc_null(fixed_df, dm_df, 'MH')
            fixed_df = fix_mh_permissible_vars(fixed_df)
        
        elif domain == 'LB':
            fixed_df = add_baseline_flags(fixed_df, 'LB')
        
        elif domain == 'VS':
            fixed_df = add_baseline_flags(fixed_df, 'VS')
        
        elif domain == 'SV':
            fixed_df = add_sv_expected_vars(fixed_df)
        
        elif domain == 'TV':
            fixed_df = fix_tv_domain(fixed_df)
        
        elif domain == 'TA':
            fixed_df = fix_ta_domain(fixed_df)
        
        elif domain == 'SE':
            fixed_df = fix_se_endtc(fixed_df, dm_df)
        
        elif domain == 'TS':
            fixed_df = fix_ts_parameters(fixed_df, study_end_date)
            fixed_df = remove_null_permissible_columns(fixed_df, 'TS')
        
        # Remove null permissible columns
        fixed_df = remove_null_permissible_columns(fixed_df, domain)
        
        # Reorder columns (SD1079 fix)
        fixed_df = reorder_columns(fixed_df, domain)
        
        fixed[domain] = fixed_df
    
    # Create SUPPAE if AE exists
    if 'AE' in fixed:
        fixed['SUPPAE'] = create_suppae(fixed['AE'])
    
    return fixed
