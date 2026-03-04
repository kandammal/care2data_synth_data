"""
SDTMIG v3.4 Variable Ordering Module

This module defines the canonical variable order for each SDTM domain
per SDTMIG v3.4 Domain Specifications.

Variables are listed in the exact order they appear in the SDTMIG tables.
Non-standard variables not in this list will be flagged for SUPP-- domains.
"""

from typing import List, Dict, Tuple
import pandas as pd
import logging

logger = logging.getLogger(__name__)

# =============================================================================
# SDTMIG v3.4 Variable Order by Domain
# Each list contains variables in exact SDTMIG specification order
# =============================================================================

SDTMIG_VARIABLE_ORDER = {
    # -------------------------------------------------------------------------
    # Demographics (DM) - SDTMIG v3.4 Section 6.1
    # -------------------------------------------------------------------------
    'DM': [
        # Identifier Variables
        'STUDYID',      # Study Identifier (Req)
        'DOMAIN',       # Domain Abbreviation (Req)
        'USUBJID',      # Unique Subject Identifier (Req)
        'SUBJID',       # Subject Identifier for the Study (Req)
        'RFSTDTC',      # Subject Reference Start Date/Time (Exp)
        'RFENDTC',      # Subject Reference End Date/Time (Exp)
        'RFXSTDTC',     # Date/Time of First Study Treatment (Exp)
        'RFXENDTC',     # Date/Time of Last Study Treatment (Exp)
        'RFICDTC',      # Date/Time of Informed Consent (Perm)
        'RFPENDTC',     # Date/Time of End of Participation (Perm)
        'DTHDTC',       # Date/Time of Death (Perm)
        'DTHFL',        # Subject Death Flag (Perm)
        'SITEID',       # Study Site Identifier (Req)
        'INVID',        # Investigator Identifier (Perm)
        'INVNAM',       # Investigator Name (Perm) - MUST follow SITEID
        'BRTHDTC',      # Date/Time of Birth (Perm)
        'AGE',          # Age (Perm)
        'AGEU',         # Age Units (Perm)
        'SEX',          # Sex (Req)
        'RACE',         # Race (Perm)
        'ETHNIC',       # Ethnicity (Perm)
        'ARMCD',        # Planned Arm Code (Req)
        'ARM',          # Description of Planned Arm (Req)
        'ACTARMCD',     # Actual Arm Code (Perm)
        'ACTARM',       # Description of Actual Arm (Perm)
        'ARMNRS',       # Reason Arm and/or Actual Arm is Null (Perm)
        'ACTARMUD',     # Description of Unplanned Actual Arm (Perm) - Required per SD0057
        'COUNTRY',      # Country (Req)
        'DMDTC',        # Date/Time of Collection (Perm)
        'DMDY',         # Study Day of Collection (Perm)
    ],

    # -------------------------------------------------------------------------
    # Adverse Events (AE) - SDTMIG v3.4 Section 6.2
    # -------------------------------------------------------------------------
    'AE': [
        # Identifier Variables
        'STUDYID',      # Study Identifier (Req)
        'DOMAIN',       # Domain Abbreviation (Req)
        'USUBJID',      # Unique Subject Identifier (Req)
        'AESEQ',        # Sequence Number (Req)
        'AEGRPID',      # Group ID (Perm)
        'AEREFID',      # Reference ID (Perm)
        'AESPID',       # Sponsor-Defined Identifier (Perm)
        'AELNKID',      # Link ID (Perm)
        'AELNKGRP',     # Link Group ID (Perm)
        # Topic Variable
        'AETERM',       # Reported Term for the Adverse Event (Req)
        'AEMODIFY',     # Modified Reported Term (Perm)
        # Synonym Qualifier Variables (MedDRA)
        'AELLT',        # Lowest Level Term (Perm)
        'AELLTCD',      # Lowest Level Term Code (Perm)
        'AEDECOD',      # Dictionary-Derived Term (Perm)
        'AEPTCD',       # Preferred Term Code (Perm)
        'AEHLT',        # High Level Term (Perm)
        'AEHLTCD',      # High Level Term Code (Perm)
        'AEHLGT',       # High Level Group Term (Perm)
        'AEHLGTCD',     # High Level Group Term Code (Perm)
        'AECAT',        # Category (Perm)
        'AESCAT',       # Subcategory (Perm)
        'AEPRESP',      # Pre-Specified (Perm)
        'AEBODSYS',     # Body System or Organ Class (Perm)
        'AEBDSYCD',     # Body System or Organ Class Code (Perm)
        'AESOC',        # Primary System Organ Class (Perm)
        'AESOCCD',      # Primary System Organ Class Code (Perm)
        'AELOC',        # Location of Event (Perm)
        # Record Qualifier Variables
        'AESEV',        # Severity/Intensity (Perm)
        'AESER',        # Serious Event (Exp)
        'AEACN',        # Action Taken with Study Treatment (Perm)
        'AEACNOTH',     # Other Action Taken (Perm)
        'AEACNDEV',     # Action Taken with Device (Perm)
        'AEREL',        # Causality (Perm)
        'AERELNST',     # Relationship to Non-Study Treatment (Perm)
        'AEPATT',       # Pattern of Event (Perm)
        'AEOUT',        # Outcome of Adverse Event (Perm)
        'AESCAN',       # Involves Cancer (Perm)
        'AESCONG',      # Congenital Anomaly or Birth Defect (Perm)
        'AESDISAB',     # Persist or Signif Disability/Incapacity (Perm)
        'AESDTH',       # Results in Death (Perm)
        'AESHOSP',      # Requires or Prolongs Hospitalization (Perm)
        'AESLIFE',      # Is Life Threatening (Perm)
        'AESOD',        # Occurred with Overdose (Perm)
        'AESMIE',       # Other Medically Important Serious Event (Perm)
        'AECONTRT',     # Concomitant or Additional Treatment Given (Perm)
        'AETOXGR',      # Standard Toxicity Grade (Perm)
        # Timing Variables
        'EPOCH',        # Epoch (Perm)
        'AESTDTC',      # Start Date/Time of Adverse Event (Exp)
        'AEENDTC',      # End Date/Time of Adverse Event (Perm)
        'AESTDY',       # Study Day of Start of Adverse Event (Perm)
        'AEENDY',       # Study Day of End of Adverse Event (Perm)
        'AEDUR',        # Duration of Adverse Event (Perm)
        'AEENRF',       # End Relative to Reference Period (Perm)
        'AEENRTPT',     # End Relative to Reference Time Point (Perm)
        'AEENTPT',      # End Reference Time Point (Perm)
        'VISITNUM',     # Visit Number (Perm)
        'VISIT',        # Visit Name (Perm)
        'VISITDY',      # Planned Study Day of Visit (Perm)
    ],

    # -------------------------------------------------------------------------
    # Concomitant Medications (CM) - SDTMIG v3.4 Section 6.3
    # -------------------------------------------------------------------------
    'CM': [
        # Identifier Variables
        'STUDYID',      # Study Identifier (Req)
        'DOMAIN',       # Domain Abbreviation (Req)
        'USUBJID',      # Unique Subject Identifier (Req)
        'CMSEQ',        # Sequence Number (Req)
        'CMGRPID',      # Group ID (Perm)
        'CMREFID',      # Reference ID (Perm)
        'CMSPID',       # Sponsor-Defined Identifier (Perm)
        'CMLNKID',      # Link ID (Perm)
        'CMLNKGRP',     # Link Group ID (Perm)
        # Topic Variable
        'CMTRT',        # Reported Name of Drug, Med, or Therapy (Req)
        'CMMODIFY',     # Modified Reported Name (Perm)
        'CMDECOD',      # Standardized Medication Name (Perm)
        'CMCAT',        # Category for Medication (Perm)
        'CMSCAT',       # Subcategory for Medication (Perm)
        'CMPRESP',      # Pre-Specified (Perm)
        'CMOCCUR',      # CM Occurrence (Perm)
        'CMSTAT',       # Completion Status (Perm)
        'CMREASND',     # Reason Not Done (Perm)
        'CMINDC',       # Indication (Perm)
        # Record Qualifier Variables
        'CMDOSE',       # Dose (Perm)
        'CMDOSTXT',     # Dose Description (Perm)
        'CMDOSU',       # Dose Units (Perm)
        'CMDOSFRM',     # Dose Form (Perm)
        'CMDOSFRQ',     # Dosing Frequency (Perm)
        'CMDOSTOT',     # Total Daily Dose (Perm)
        'CMDOSRGM',     # Intended Dose Regimen (Perm)
        'CMROUTE',      # Route of Administration (Perm)
        'CMLOC',        # Location (Perm)
        'CMLAT',        # Laterality (Perm)
        'CMDIR',        # Directionality (Perm)
        'CMPORTOT',     # Portion or Totality (Perm)
        'CMFAST',       # Fasting Status (Perm)
        'CMADJ',        # Adjustment (Perm)
        'CMCLASCD',     # Medication Class Code (Perm)
        'CMCLAS',       # Medication Class (Perm)
        # Timing Variables
        'EPOCH',        # Epoch (Perm)
        'CMSTDTC',      # Start Date/Time (Perm)
        'CMENDTC',      # End Date/Time (Perm)
        'CMSTDY',       # Study Day of Start (Perm)
        'CMENDY',       # Study Day of End (Perm)
        'CMDUR',        # Duration (Perm)
        'CMSTRF',       # Start Relative to Reference Period (Perm)
        'CMENRF',       # End Relative to Reference Period (Perm)
        'CMSTRTPT',     # Start Relative to Reference Time Point (Perm)
        'CMSTTPT',      # Start Reference Time Point (Perm)
        'CMENRTPT',     # End Relative to Reference Time Point (Perm)
        'CMENTPT',      # End Reference Time Point (Perm)
        'VISITNUM',     # Visit Number (Perm)
        'VISIT',        # Visit Name (Perm)
        'VISITDY',      # Planned Study Day of Visit (Perm)
    ],

    # -------------------------------------------------------------------------
    # Disposition (DS) - SDTMIG v3.4 Section 6.4
    # -------------------------------------------------------------------------
    'DS': [
        # Identifier Variables
        'STUDYID',      # Study Identifier (Req)
        'DOMAIN',       # Domain Abbreviation (Req)
        'USUBJID',      # Unique Subject Identifier (Req)
        'DSSEQ',        # Sequence Number (Req)
        'DSGRPID',      # Group ID (Perm)
        'DSREFID',      # Reference ID (Perm)
        'DSSPID',       # Sponsor-Defined Identifier (Perm)
        'DSLNKID',      # Link ID (Perm)
        'DSLNKGRP',     # Link Group ID (Perm)
        # Topic Variable
        'DSTERM',       # Reported Term for the Disposition Event (Req)
        'DSDECOD',      # Standardized Disposition Term (Perm)
        'DSCAT',        # Category for Disposition Event (Perm)
        'DSSCAT',       # Subcategory for Disposition Event (Perm)
        # Timing Variables
        'EPOCH',        # Epoch (Perm)
        'DSSTDTC',      # Start Date/Time of Disposition Event (Perm)
        'DSENDTC',      # End Date/Time of Disposition Event (Perm)
        'DSSTDY',       # Study Day of Start of Disposition Event (Perm)
        'DSENDY',       # Study Day of End of Disposition Event (Perm)
        'DSDUR',        # Duration (Perm)
        'VISITNUM',     # Visit Number (Perm)
        'VISIT',        # Visit Name (Perm)
        'VISITDY',      # Planned Study Day of Visit (Perm)
    ],

    # -------------------------------------------------------------------------
    # Exposure (EX) - SDTMIG v3.4 Section 6.5
    # Note: VISIT/VISITNUM removed per SD1076 - only include if dosing tied to visits
    # -------------------------------------------------------------------------
    'EX': [
        # Identifier Variables
        'STUDYID',      # Study Identifier (Req)
        'DOMAIN',       # Domain Abbreviation (Req)
        'USUBJID',      # Unique Subject Identifier (Req)
        'EXSEQ',        # Sequence Number (Req)
        'EXGRPID',      # Group ID (Perm)
        'EXREFID',      # Reference ID (Perm)
        'EXSPID',       # Sponsor-Defined Identifier (Perm)
        'EXLNKID',      # Link ID (Perm)
        'EXLNKGRP',     # Link Group ID (Perm)
        # Topic Variable
        'EXTRT',        # Name of Treatment (Req)
        'EXCAT',        # Category for Treatment (Perm)
        'EXSCAT',       # Subcategory for Treatment (Perm)
        # Record Qualifier Variables
        'EXDOSE',       # Dose (Perm)
        'EXDOSTXT',     # Dose Description (Perm)
        'EXDOSU',       # Dose Units (Perm)
        'EXDOSFRM',     # Dose Form (Perm)
        'EXDOSFRQ',     # Dosing Frequency (Perm)
        'EXDOSRGM',     # Intended Dose Regimen (Perm)
        'EXROUTE',      # Route of Administration (Perm)
        'EXLOT',        # Lot Number (Perm)
        'EXLOC',        # Location of Dose Administration (Perm)
        'EXLAT',        # Laterality (Perm)
        'EXDIR',        # Directionality (Perm)
        'EXFAST',       # Fasting Status (Perm)
        'EXADJ',        # Reason for Dose Adjustment (Perm)
        # Timing Variables - No VISIT/VISITNUM per SD1076 for continuous dosing
        'EPOCH',        # Epoch (Perm)
        'EXSTDTC',      # Start Date/Time of Treatment (Perm)
        'EXENDTC',      # End Date/Time of Treatment (Perm)
        'EXSTDY',       # Study Day of Start of Treatment (Perm)
        'EXENDY',       # Study Day of End of Treatment (Perm)
        'EXDUR',        # Duration of Treatment (Perm)
        'EXTPT',        # Planned Time Point Name (Perm)
        'EXTPTNUM',     # Planned Time Point Number (Perm)
        'EXELTM',       # Planned Elapsed Time from Time Point Ref (Perm)
        'EXTPTREF',     # Time Point Reference (Perm)
        'EXRFTDTC',     # Date/Time of Reference Time Point (Perm)
    ],

    # -------------------------------------------------------------------------
    # Laboratory Test Results (LB) - SDTMIG v3.4 Section 6.6
    # -------------------------------------------------------------------------
    'LB': [
        # Identifier Variables
        'STUDYID',      # Study Identifier (Req)
        'DOMAIN',       # Domain Abbreviation (Req)
        'USUBJID',      # Unique Subject Identifier (Req)
        'LBSEQ',        # Sequence Number (Req)
        'LBGRPID',      # Group ID (Perm)
        'LBREFID',      # Reference ID (Perm)
        'LBSPID',       # Sponsor-Defined Identifier (Perm)
        'LBLNKID',      # Link ID (Perm)
        'LBLNKGRP',     # Link Group ID (Perm)
        # Topic Variable
        'LBTESTCD',     # Lab Test Short Name (Req)
        'LBTEST',       # Lab Test or Examination Name (Req)
        'LBCAT',        # Category for Lab Test (Perm)
        'LBSCAT',       # Subcategory for Lab Test (Perm)
        # Result Qualifier Variables
        'LBORRES',      # Result or Finding in Original Units (Perm)
        'LBORRESU',     # Original Units (Perm)
        'LBORNRLO',     # Reference Range Lower Limit-Orig Unit (Perm)
        'LBORNRHI',     # Reference Range Upper Limit-Orig Unit (Perm)
        'LBSTRESC',     # Character Result/Finding in Std Format (Perm)
        'LBSTRESN',     # Numeric Result/Finding in Standard Units (Perm)
        'LBSTRESU',     # Standard Units (Perm)
        'LBSTNRLO',     # Reference Range Lower Limit-Std Units (Perm)
        'LBSTNRHI',     # Reference Range Upper Limit-Std Units (Perm)
        'LBSTNRC',      # Reference Range for Char Result-Std Units (Perm)
        'LBNRIND',      # Reference Range Indicator (Perm)
        'LBRESSCL',     # Result Scale Classification (Perm) - QUANTITATIVE/ORDINAL/NOMINAL
        'LBSTAT',       # Completion Status (Perm)
        'LBREASND',     # Reason Not Done (Perm)
        'LBNAM',        # Vendor Name (Perm)
        'LBLOINC',      # LOINC Code (Perm)
        'LBSPEC',       # Specimen Type (Perm)
        'LBSPCCND',     # Specimen Condition (Perm)
        'LBMETHOD',     # Method of Test or Examination (Perm)
        'LBLOC',        # Location (Perm)
        'LBLAT',        # Laterality (Perm)
        'LBDIR',        # Directionality (Perm)
        'LBPORTOT',     # Portion or Totality (Perm)
        # Flag Variables - LBLOBXFL comes BEFORE LBBLFL per SDTMIG spec
        'LBLOBXFL',     # Last Observation Before Exposure Flag (Perm)
        'LBBLFL',       # Baseline Flag (Perm)
        'LBFAST',       # Fasting Status (Perm)
        'LBDRVFL',      # Derived Flag (Perm)
        'LBTOX',        # Toxicity (Perm)
        'LBTOXGR',      # Standard Toxicity Grade (Perm)
        # Timing Variables - VISITNUM before VISIT, before EPOCH
        'VISITNUM',     # Visit Number (Perm)
        'VISIT',        # Visit Name (Perm)
        'VISITDY',      # Planned Study Day of Visit (Perm)
        'EPOCH',        # Epoch (Perm)
        'LBDTC',        # Date/Time of Collection (Perm)
        'LBENDTC',      # End Date/Time of Collection (Perm)
        'LBDY',         # Study Day of Visit/Collection (Perm)
        'LBENDY',       # Study Day of End of Collection (Perm)
        'LBTPT',        # Planned Time Point Name (Perm)
        'LBTPTNUM',     # Planned Time Point Number (Perm)
        'LBELTM',       # Planned Elapsed Time from Time Point Ref (Perm)
        'LBTPTREF',     # Time Point Reference (Perm)
        'LBRFTDTC',     # Date/Time of Reference Time Point (Perm)
    ],

    # -------------------------------------------------------------------------
    # Medical History (MH) - SDTMIG v3.4 Section 6.7
    # -------------------------------------------------------------------------
    'MH': [
        # Identifier Variables
        'STUDYID',      # Study Identifier (Req)
        'DOMAIN',       # Domain Abbreviation (Req)
        'USUBJID',      # Unique Subject Identifier (Req)
        'MHSEQ',        # Sequence Number (Req)
        'MHGRPID',      # Group ID (Perm)
        'MHREFID',      # Reference ID (Perm)
        'MHSPID',       # Sponsor-Defined Identifier (Perm)
        'MHLNKID',      # Link ID (Perm)
        'MHLNKGRP',     # Link Group ID (Perm)
        # Topic Variable
        'MHTERM',       # Reported Term for the Medical History (Req)
        'MHMODIFY',     # Modified Reported Term (Perm)
        'MHDECOD',      # Dictionary-Derived Term (Perm)
        'MHCAT',        # Category for Medical History (Perm)
        'MHSCAT',       # Subcategory for Medical History (Perm)
        'MHPRESP',      # Pre-Specified (Perm)
        'MHOCCUR',      # MH Occurrence (Perm)
        'MHSTAT',       # Completion Status (Perm)
        'MHREASND',     # Reason Not Done (Perm)
        'MHBODSYS',     # Body System or Organ Class (Perm)
        'MHBDSYCD',     # Body System or Organ Class Code (Perm)
        'MHLOC',        # Location of Event (Perm)
        'MHLAT',        # Laterality (Perm)
        'MHSEV',        # Severity/Intensity (Perm)
        'MHTOXGR',      # Standard Toxicity Grade (Perm)
        # Timing Variables
        'EPOCH',        # Epoch (Perm)
        'MHSTDTC',      # Start Date/Time of Medical History Event (Perm)
        'MHENDTC',      # End Date/Time of Medical History Event (Perm)
        'MHSTDY',       # Study Day of Start of MH Event (Perm)
        'MHENDY',       # Study Day of End of MH Event (Perm)
        'MHDUR',        # Duration (Perm)
        'MHSTRF',       # Start Relative to Reference Period (Perm)
        'MHENRF',       # End Relative to Reference Period (Perm)
        'MHSTRTPT',     # Start Relative to Reference Time Point (Perm)
        'MHSTTPT',      # Start Reference Time Point (Perm)
        'MHENRTPT',     # End Relative to Reference Time Point (Perm)
        'MHENTPT',      # End Reference Time Point (Perm)
        'VISITNUM',     # Visit Number (Perm)
        'VISIT',        # Visit Name (Perm)
        'VISITDY',      # Planned Study Day of Visit (Perm)
    ],

    # -------------------------------------------------------------------------
    # Subject Elements (SE) - SDTMIG v3.4 Section 6.8
    # -------------------------------------------------------------------------
    'SE': [
        # Identifier Variables
        'STUDYID',      # Study Identifier (Req)
        'DOMAIN',       # Domain Abbreviation (Req)
        'USUBJID',      # Unique Subject Identifier (Req)
        'SESEQ',        # Sequence Number (Perm) - early with identifiers
        'SEGRPID',      # Group ID (Perm)
        'SEREFID',      # Reference ID (Perm)
        'SESPID',       # Sponsor-Defined Identifier (Perm)
        'SELNKID',      # Link ID (Perm)
        'SELNKGRP',     # Link Group ID (Perm)
        # Topic/Qualifier Variables
        'ETCD',         # Element Code (Perm)
        'ELEMENT',      # Description of Element (Perm)
        'TAETORD',      # Planned Order of Element within Arm (Perm) - before EPOCH
        'SEUPDES',      # Description of Unplanned Element (Perm)
        # Timing Variables - EPOCH before dates
        'EPOCH',        # Epoch (Perm)
        'SESTDTC',      # Start Date/Time of Element (Perm)
        'SEENDTC',      # End Date/Time of Element (Perm)
        'SESTDY',       # Study Day of Start of Element (Perm)
        'SEENDY',       # Study Day of End of Element (Perm)
    ],

    # -------------------------------------------------------------------------
    # Subject Visits (SV) - SDTMIG v3.4 Section 6.9
    # -------------------------------------------------------------------------
    'SV': [
        # Identifier Variables
        'STUDYID',      # Study Identifier (Req)
        'DOMAIN',       # Domain Abbreviation (Req)
        'USUBJID',      # Unique Subject Identifier (Req)
        'SVSEQ',        # Sequence Number (Perm)
        'SVGRPID',      # Group ID (Perm)
        'SVREFID',      # Reference ID (Perm)
        'SVSPID',       # Sponsor-Defined Identifier (Perm)
        'SVLNKID',      # Link ID (Perm)
        'SVLNKGRP',     # Link Group ID (Perm)
        # Visit Variables - VISITNUM before VISIT (no VISITDY yet)
        'VISITNUM',     # Visit Number (Req)
        'VISIT',        # Visit Name (Perm)
        # Qualifier Variables - SVPRESP before SVOCCUR
        'SVPRESP',      # Pre-Specified (Perm)
        'SVOCCUR',      # Visit Occurrence (Perm)
        'SVREASOC',     # Reason for Occurrence (Perm)
        'SVCNTMOD',     # Contact Mode (Perm)
        'SVEPCHGI',     # Epoch Change Indicator (Perm)
        'SVUPDES',      # Description of Unplanned Visit (Perm)
        # Timing Variables - VISITDY comes AFTER qualifiers, before dates per SDTMIG
        'VISITDY',      # Planned Study Day of Visit (Perm)
        'EPOCH',        # Epoch (Perm)
        'SVSTDTC',      # Start Date/Time of Visit (Perm)
        'SVENDTC',      # End Date/Time of Visit (Perm)
        'SVSTDY',       # Study Day of Start of Visit (Perm)
        'SVENDY',       # Study Day of End of Visit (Perm)
    ],

    # -------------------------------------------------------------------------
    # Vital Signs (VS) - SDTMIG v3.4 Section 6.10
    # -------------------------------------------------------------------------
    'VS': [
        # Identifier Variables
        'STUDYID',      # Study Identifier (Req)
        'DOMAIN',       # Domain Abbreviation (Req)
        'USUBJID',      # Unique Subject Identifier (Req)
        'VSSEQ',        # Sequence Number (Req)
        'VSGRPID',      # Group ID (Perm)
        'VSREFID',      # Reference ID (Perm)
        'VSSPID',       # Sponsor-Defined Identifier (Perm)
        'VSLNKID',      # Link ID (Perm)
        'VSLNKGRP',     # Link Group ID (Perm)
        # Topic Variable
        'VSTESTCD',     # Vital Signs Test Short Name (Req)
        'VSTEST',       # Vital Signs Test Name (Req)
        'VSCAT',        # Category for Vital Signs (Perm)
        'VSSCAT',       # Subcategory for Vital Signs (Perm)
        'VSPOS',        # Vital Signs Position of Subject (Perm)
        # Result Qualifier Variables
        'VSORRES',      # Result or Finding in Original Units (Perm)
        'VSORRESU',     # Original Units (Perm)
        'VSSTRESC',     # Character Result/Finding in Std Format (Perm)
        'VSSTRESN',     # Numeric Result/Finding in Standard Units (Perm)
        'VSSTRESU',     # Standard Units (Perm)
        'VSSTAT',       # Completion Status (Perm)
        'VSREASND',     # Reason Not Done (Perm)
        'VSLOC',        # Location (Perm)
        'VSLAT',        # Laterality (Perm)
        # Flag Variables - VSLOBXFL comes BEFORE VSBLFL per SDTMIG spec
        'VSLOBXFL',     # Last Observation Before Exposure Flag (Perm)
        'VSBLFL',       # Baseline Flag (Perm)
        'VSDRVFL',      # Derived Flag (Perm)
        # Timing Variables - VISITNUM before VISIT, before EPOCH/dates
        'VISITNUM',     # Visit Number (Perm)
        'VISIT',        # Visit Name (Perm)
        'VISITDY',      # Planned Study Day of Visit (Perm)
        'EPOCH',        # Epoch (Perm)
        'VSDTC',        # Date/Time of Measurements (Perm)
        'VSENDTC',      # End Date/Time of Measurements (Perm)
        'VSDY',         # Study Day of Vital Signs (Perm)
        'VSENDY',       # Study Day of End of Measurements (Perm)
        'VSTPT',        # Planned Time Point Name (Perm)
        'VSTPTNUM',     # Planned Time Point Number (Perm)
        'VSELTM',       # Planned Elapsed Time from Time Point Ref (Perm)
        'VSTPTREF',     # Time Point Reference (Perm)
        'VSRFTDTC',     # Date/Time of Reference Time Point (Perm)
    ],

    # -------------------------------------------------------------------------
    # Trial Arms (TA) - SDTMIG v3.4 Section 7.1
    # -------------------------------------------------------------------------
    'TA': [
        'STUDYID',      # Study Identifier (Req)
        'DOMAIN',       # Domain Abbreviation (Req)
        'ARMCD',        # Planned Arm Code (Req)
        'ARM',          # Description of Planned Arm (Req)
        'TAETORD',      # Planned Order of Element within Arm (Req)
        'ETCD',         # Element Code (Req)
        'ELEMENT',      # Description of Element (Req)
        'TABRANCH',     # Branch (Perm)
        'TATRANS',      # Transition Rule (Perm)
        'EPOCH',        # Epoch (Req)
    ],

    # -------------------------------------------------------------------------
    # Trial Elements (TE) - SDTMIG v3.4 Section 7.2
    # -------------------------------------------------------------------------
    'TE': [
        'STUDYID',      # Study Identifier (Req)
        'DOMAIN',       # Domain Abbreviation (Req)
        'ETCD',         # Element Code (Req)
        'ELEMENT',      # Description of Element (Req)
        'TESTRL',       # Rule for Start of Element (Perm)
        'TEENRL',       # Rule for End of Element (Perm)
        'TEDUR',        # Planned Duration of Element (Perm)
    ],

    # -------------------------------------------------------------------------
    # Trial Inclusion/Exclusion Criteria (TI) - SDTMIG v3.4 Section 7.3
    # -------------------------------------------------------------------------
    'TI': [
        'STUDYID',      # Study Identifier (Req)
        'DOMAIN',       # Domain Abbreviation (Req)
        'IETESTCD',     # Inclusion/Exclusion Criterion Short Name (Req)
        'IETEST',       # Inclusion/Exclusion Criterion (Req)
        'IECAT',        # Inclusion/Exclusion Category (Req)
        'IESCAT',       # Inclusion/Exclusion Subcategory (Perm)
        'TIRL',         # Inclusion/Exclusion Criterion Rule (Perm)
        'TIVERS',       # Protocol Criteria Versions (Perm)
    ],

    # -------------------------------------------------------------------------
    # Trial Summary (TS) - SDTMIG v3.4 Section 7.4
    # -------------------------------------------------------------------------
    'TS': [
        'STUDYID',      # Study Identifier (Req)
        'DOMAIN',       # Domain Abbreviation (Req)
        'TSSEQ',        # Sequence Number (Req)
        'TSGRPID',      # Group ID (Perm)
        'TSPARMCD',     # Trial Summary Parameter Short Name (Req)
        'TSPARM',       # Trial Summary Parameter (Req)
        'TSVAL',        # Parameter Value (Exp)
        'TSVALNF',      # Parameter Null Flavor (Perm)
        'TSVALCD',      # Parameter Value Code (Perm)
        'TSVCDREF',     # Name of Reference Terminology (Perm)
        'TSVCDVER',     # Version of Reference Terminology (Perm)
    ],

    # -------------------------------------------------------------------------
    # Trial Visits (TV) - SDTMIG v3.4 Section 7.5
    # -------------------------------------------------------------------------
    'TV': [
        'STUDYID',      # Study Identifier (Req)
        'DOMAIN',       # Domain Abbreviation (Req)
        'VISITNUM',     # Visit Number (Req)
        'VISIT',        # Visit Name (Perm)
        'VISITDY',      # Planned Study Day of Visit (Perm)
        'ARMCD',        # Planned Arm Code (Perm)
        'ARM',          # Description of Planned Arm (Perm)
        'TVSTRL',       # Visit Start Rule (Perm)
        'TVENRL',       # Visit End Rule (Perm)
    ],

    # -------------------------------------------------------------------------
    # Related Records (RELREC) - SDTMIG v3.4 Section 8.4
    # -------------------------------------------------------------------------
    'RELREC': [
        'STUDYID',      # Study Identifier (Req)
        'RDOMAIN',      # Related Domain Abbreviation (Req)
        'USUBJID',      # Unique Subject Identifier (Exp)
        'IDVAR',        # Identifying Variable (Req)
        'IDVARVAL',     # Identifying Variable Value (Req)
        'RELTYPE',      # Relationship Type (Perm)
        'RELID',        # Relationship Identifier (Perm)
    ],

    # -------------------------------------------------------------------------
    # Supplemental Qualifier (SUPP--) - SDTMIG v3.4 Section 8
    # -------------------------------------------------------------------------
    'SUPPAE': [
        'STUDYID',      # Study Identifier (Req)
        'RDOMAIN',      # Related Domain Abbreviation (Req)
        'USUBJID',      # Unique Subject Identifier (Req)
        'IDVAR',        # Identifying Variable (Perm)
        'IDVARVAL',     # Identifying Variable Value (Perm)
        'QNAM',         # Qualifier Variable Name (Req)
        'QLABEL',       # Qualifier Variable Label (Req)
        'QVAL',         # Data Value (Req)
        'QORIG',        # Origin (Req)
        'QEVAL',        # Evaluator (Perm)
    ],

    # Generic SUPP template (applies to all SUPP-- domains)
    'SUPP': [
        'STUDYID',
        'RDOMAIN',
        'USUBJID',
        'IDVAR',
        'IDVARVAL',
        'QNAM',
        'QLABEL',
        'QVAL',
        'QORIG',
        'QEVAL',
    ],
}

# Copy SUPP template to common SUPP domains
for supp_domain in ['SUPPCM', 'SUPPDS', 'SUPPEX', 'SUPPLB', 'SUPPMH', 'SUPPVS', 
                    'SUPPDM', 'SUPPSV', 'SUPPTV']:
    SDTMIG_VARIABLE_ORDER[supp_domain] = SDTMIG_VARIABLE_ORDER['SUPP'].copy()


def reorder_columns_sdtmig(df: pd.DataFrame, domain: str) -> pd.DataFrame:
    """
    Reorder DataFrame columns to match SDTMIG v3.4 variable order.
    
    Args:
        df: DataFrame to reorder
        domain: SDTM domain name (e.g., 'DM', 'AE', 'LB')
    
    Returns:
        DataFrame with columns in SDTMIG order
    
    Non-standard variables (not in SDTMIG) are flagged with a warning
    and appended at the end. In production, these should be moved to SUPP--.
    """
    if df.empty:
        return df
    
    domain_upper = domain.upper()
    
    # Get canonical order for this domain
    if domain_upper not in SDTMIG_VARIABLE_ORDER:
        logger.warning(f"No SDTMIG variable order defined for domain '{domain_upper}'")
        return df
    
    canonical_order = SDTMIG_VARIABLE_ORDER[domain_upper]
    
    # Separate columns into: (1) in canonical order, (2) non-standard
    current_cols = list(df.columns)
    ordered_cols = []
    non_standard_cols = []
    
    # Add columns that exist in both, preserving SDTMIG order
    for col in canonical_order:
        if col in current_cols:
            ordered_cols.append(col)
    
    # Find non-standard columns (exist in data but not in SDTMIG spec)
    for col in current_cols:
        if col not in canonical_order:
            non_standard_cols.append(col)
            logger.debug(f"Non-standard variable '{col}' in {domain_upper} "
                        f"(should be in SUPP{domain_upper})")
    
    # Final order: SDTMIG columns first, then non-standard
    final_order = ordered_cols + non_standard_cols
    
    return df[final_order]


def identify_nonstandard_variables(df: pd.DataFrame, domain: str) -> Tuple[List[str], List[str]]:
    """
    Identify which variables are standard vs non-standard for a domain.
    
    Args:
        df: DataFrame to check
        domain: SDTM domain name
    
    Returns:
        Tuple of (standard_vars, nonstandard_vars)
    """
    domain_upper = domain.upper()
    
    if domain_upper not in SDTMIG_VARIABLE_ORDER:
        return list(df.columns), []
    
    canonical = set(SDTMIG_VARIABLE_ORDER[domain_upper])
    current = set(df.columns)
    
    standard = [c for c in df.columns if c in canonical]
    nonstandard = [c for c in df.columns if c not in canonical]
    
    return standard, nonstandard


def move_to_supp(df: pd.DataFrame, domain: str, 
                 exclude_vars: List[str] = None) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """
    Move non-standard variables from main domain to SUPP-- dataset.
    
    Args:
        df: Main domain DataFrame
        domain: Domain name (e.g., 'AE')
        exclude_vars: Variables to keep in main domain even if non-standard
    
    Returns:
        Tuple of (cleaned main domain df, SUPP-- df)
    """
    if exclude_vars is None:
        exclude_vars = []
    
    domain_upper = domain.upper()
    standard_vars, nonstandard_vars = identify_nonstandard_variables(df, domain)
    
    # Filter out excluded vars from nonstandard
    vars_to_move = [v for v in nonstandard_vars if v not in exclude_vars]
    
    if not vars_to_move:
        return df, pd.DataFrame()
    
    # Determine the sequence variable for this domain
    seq_var = f'{domain_upper[:2]}SEQ'
    if seq_var not in df.columns:
        # Try to find any SEQ variable
        seq_cols = [c for c in df.columns if c.endswith('SEQ')]
        seq_var = seq_cols[0] if seq_cols else None
    
    # Build SUPP-- records
    supp_records = []
    for idx, row in df.iterrows():
        for var in vars_to_move:
            val = row.get(var)
            if pd.notna(val) and str(val).strip() != '':
                supp_records.append({
                    'STUDYID': row.get('STUDYID', ''),
                    'RDOMAIN': domain_upper,
                    'USUBJID': row.get('USUBJID', ''),
                    'IDVAR': seq_var if seq_var else '',
                    'IDVARVAL': str(row.get(seq_var, '')) if seq_var else '',
                    'QNAM': var,
                    'QLABEL': var,  # Should be proper label
                    'QVAL': str(val),
                    'QORIG': 'CRF',
                    'QEVAL': ''
                })
    
    # Create SUPP DataFrame
    supp_df = pd.DataFrame(supp_records) if supp_records else pd.DataFrame()
    
    # Remove non-standard vars from main domain
    keep_cols = [c for c in df.columns if c not in vars_to_move]
    main_df = df[keep_cols]
    
    return main_df, supp_df
