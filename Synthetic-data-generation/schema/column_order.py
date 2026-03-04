"""
Column order, row sort keys, and SEQ ordering rules — Contract 8 & 10.

These are frozen constants generated once from SDTMIG v3.4.
Changes require a version bump and re-baselining of Test 6.
"""

DOMAIN_COLUMN_ORDER = {
    "DM": [
        "STUDYID", "DOMAIN", "USUBJID", "SUBJID", "SITEID",
        "BRTHDTC", "AGE", "AGEU", "SEX", "RACE", "ETHNIC",
        "ARMCD", "ARM", "ACTARMCD", "ACTARM", "ARMNRS",
        "COUNTRY", "INVNAM",
        "RFSTDTC", "RFENDTC", "RFXSTDTC", "RFXENDTC",
        "RFICDTC", "RFPENDTC", "DTHDTC", "DTHFL",
    ],
    "AE": [
        "STUDYID", "DOMAIN", "USUBJID", "AESEQ", "AELNKID",
        "AETERM", "AEDECOD", "AEPTCD",
        "AEHLT", "AEHLTCD", "AEHLGT", "AEHLGTCD",
        "AEBODSYS", "AEBDSYCD", "AESOC", "AESOCCD",
        "AESEV", "AESER", "AESDTH", "AEREL", "AEOUT", "AEACN",
        "AESTDTC", "AEENDTC", "AESTDY", "AEENDY", "EPOCH",
    ],
    "DS": [
        "STUDYID", "DOMAIN", "USUBJID", "DSSEQ",
        "DSTERM", "DSDECOD", "DSCAT", "DSSCAT", "DSLNKID",
        "DSSTDTC", "DSSTDY", "EPOCH",
    ],
    "EX": [
        "STUDYID", "DOMAIN", "USUBJID", "EXSEQ",
        "EXTRT", "EXDOSE", "EXDOSU", "EXDOSFRM", "EXDOSFRQ",
        "EXROUTE", "EXSTDTC", "EXENDTC", "EXSTDY", "EXENDY",
        "VISITNUM", "VISIT", "EPOCH",
    ],
    "LB": [
        "STUDYID", "DOMAIN", "USUBJID", "LBSEQ",
        "LBTESTCD", "LBTEST", "LBCAT",
        "LBORRES", "LBORRESU", "LBORNRLO", "LBORNRHI",
        "LBSTRESC", "LBSTRESN", "LBSTRESU", "LBSTNRLO", "LBSTNRHI",
        "LBNRIND", "LBSTAT", "LBSPEC", "LBMETHOD",
        "LBDTC", "LBDY", "VISITNUM", "VISIT", "EPOCH",
    ],
    "VS": [
        "STUDYID", "DOMAIN", "USUBJID", "VSSEQ",
        "VSTESTCD", "VSTEST",
        "VSORRES", "VSORRESU", "VSSTRESC", "VSSTRESN", "VSSTRESU",
        "VSSTAT", "VSPOS", "VSLOC", "VSBLFL",
        "VSDTC", "VSDY", "VISITNUM", "VISIT", "EPOCH",
    ],
    "CM": [
        "STUDYID", "DOMAIN", "USUBJID", "CMSEQ",
        "CMTRT", "CMDECOD", "CMCAT",
        "CMDOSE", "CMDOSU", "CMDOSFRQ", "CMROUTE",
        "CMSTDTC", "CMENDTC", "CMSTDY", "CMENDY",
        "CMINDC", "EPOCH",
    ],
    "MH": [
        "STUDYID", "DOMAIN", "USUBJID", "MHSEQ",
        "MHTERM", "MHDECOD", "MHCAT", "MHSCAT", "MHBODSYS",
        "MHSTDTC", "MHENDTC", "MHENRF", "MHDY", "EPOCH",
    ],
    "SE": [
        "STUDYID", "DOMAIN", "USUBJID", "SESEQ",
        "ETCD", "ELEMENT",
        "SESTDTC", "SEENDTC", "SESTDY", "SEENDY", "EPOCH",
    ],
    "SV": [
        "STUDYID", "DOMAIN", "USUBJID", "SVSEQ",
        "VISITNUM", "VISIT",
        "SVSTDTC", "SVENDTC", "SVSTDY", "SVENDY", "EPOCH",
    ],
}

# Contract 10: Row sort keys per domain
DOMAIN_ROW_SORT_KEYS = {
    "AE":     ["USUBJID", "AESEQ"],
    "CM":     ["USUBJID", "CMSEQ"],
    "DM":     ["USUBJID"],
    "DS":     ["USUBJID", "DSSEQ"],
    "EX":     ["USUBJID", "EXSEQ"],
    "LB":     ["USUBJID", "LBSEQ"],
    "MH":     ["USUBJID", "MHSEQ"],
    "SE":     ["USUBJID", "SESEQ"],
    "SV":     ["USUBJID", "SVSEQ"],
    "VS":     ["USUBJID", "VSSEQ"],
    "RELREC": ["USUBJID", "RELID", "RDOMAIN", "IDVARVAL"],
}

# Contract 8: SEQ ordering rules
SEQ_ORDER_RULES = {
    "AE":  "sort by onset_date ascending, then canonical_id for ties",
    "DS":  "sort by date ascending, then canonical_id for ties",
    "LB":  "sort by (period, visitnum, testcd) lexicographically",
    "VS":  "sort by (period, visitnum, testcd) lexicographically",
    "EX":  "sort by (period, start_date) ascending",
    "CM":  "sort by start_date ascending, then canonical_id for ties",
    "MH":  "sort by term alphabetically",
    "SV":  "sort by (visitnum) ascending",
    "SE":  "sort by (start_date) ascending",
}
