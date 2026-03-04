"""
Protocol Specification Extractor.
"""

from __future__ import annotations
from typing import Optional, List
from sdtm_synth.spec.models import (
    TrialDesignSpec, ArmSpec, ElementSpec, ArmPath, ArmPathItem,
    VisitSpec, RegimenItem, TSParameter, CollectionFlags, Route, DoseFrequency, Assumption,
    DemographicsDefaults, AEModelDefaults, AETermProfile, DispositionModelDefaults
)


def extract_bendita_spec() -> TrialDesignSpec:
    """Create specification for BENDITA trial (Chagas disease, Phase 2)."""
    arms = [
        ArmSpec(armcd="BZN8W", arm="BZN 300mg 8 weeks", regimen=[
            RegimenItem(extrt="BENZNIDAZOLE", dose=150, dose_unit="mg", route=Route.ORAL, frequency=DoseFrequency.BID)
        ]),
        ArmSpec(armcd="BZN4W", arm="BZN 300mg 4 weeks", regimen=[
            RegimenItem(extrt="BENZNIDAZOLE", dose=150, dose_unit="mg", route=Route.ORAL, frequency=DoseFrequency.BID)
        ]),
        ArmSpec(armcd="BZN2W", arm="BZN 300mg 2 weeks", regimen=[
            RegimenItem(extrt="BENZNIDAZOLE", dose=150, dose_unit="mg", route=Route.ORAL, frequency=DoseFrequency.BID)
        ]),
        ArmSpec(armcd="E1224H", arm="E1224 High Dose", regimen=[
            RegimenItem(extrt="E1224", dose=400, dose_unit="mg", route=Route.ORAL, frequency=DoseFrequency.QD)
        ]),
        ArmSpec(armcd="E1224L", arm="E1224 Low Dose", regimen=[
            RegimenItem(extrt="E1224", dose=200, dose_unit="mg", route=Route.ORAL, frequency=DoseFrequency.QD)
        ]),
        ArmSpec(armcd="COMBO", arm="BZN + E1224 Combination", regimen=[
            RegimenItem(extrt="BENZNIDAZOLE", dose=150, dose_unit="mg", route=Route.ORAL, frequency=DoseFrequency.BID),
            RegimenItem(extrt="E1224", dose=200, dose_unit="mg", route=Route.ORAL, frequency=DoseFrequency.QD)
        ]),
        ArmSpec(armcd="PBO", arm="Placebo", regimen=[
            RegimenItem(extrt="PLACEBO", dose=0, dose_unit="mg", route=Route.ORAL, frequency=DoseFrequency.BID)
        ]),
    ]
    
    elements = [
        ElementSpec(etcd="SCRN", element="Screening", epoch="SCREENING", nominal_duration_days=40,
                   start_rule="Informed consent", end_rule="Before randomization"),
        ElementSpec(etcd="TRT", element="Treatment", epoch="TREATMENT", nominal_duration_days=56,
                   start_rule="Randomization (Day 0)", end_rule="End of treatment (Week 8)"),
        ElementSpec(etcd="FU", element="Follow-up", epoch="FOLLOW-UP", nominal_duration_days=336,
                   start_rule="End of treatment", end_rule="12 months follow-up"),
    ]
    
    arm_paths = [ArmPath(armcd=arm.armcd, elements=[
        ArmPathItem(etcd="SCRN", taetord=1),
        ArmPathItem(etcd="TRT", taetord=2),
        ArmPathItem(etcd="FU", taetord=3),
    ]) for arm in arms]
    
    visits = [
        # Screening: nominal day -20, window allows [-20, +20] = actual day range [-40, 0]
        # Note: dates after RFSTDTC are capped to RFSTDTC for screening visits
        VisitSpec(visitnum=1, visit="SCREENING", nominal_day=-20, window_lower=-20, window_upper=20, epoch="SCREENING",
                 collection_flags=CollectionFlags(mh=True, lb=True, vs=True, ae=False, ex=False)),
        VisitSpec(visitnum=2, visit="BASELINE", nominal_day=-1, window_lower=-1, window_upper=0, epoch="SCREENING",
                 collection_flags=CollectionFlags(lb=True, vs=True, ex=False)),
        VisitSpec(visitnum=3, visit="DAY 1", nominal_day=1, window_lower=0, window_upper=0, epoch="TREATMENT",
                 collection_flags=CollectionFlags(ex=True, vs=True)),
        VisitSpec(visitnum=4, visit="DAY 2", nominal_day=2, window_lower=0, window_upper=0, epoch="TREATMENT",
                 collection_flags=CollectionFlags(ex=True, vs=True)),
        VisitSpec(visitnum=5, visit="DAY 3", nominal_day=3, window_lower=0, window_upper=0, epoch="TREATMENT",
                 collection_flags=CollectionFlags(ex=True, lb=True, vs=True)),
        VisitSpec(visitnum=6, visit="WEEK 2", nominal_day=14, window_lower=-2, window_upper=2, epoch="TREATMENT",
                 collection_flags=CollectionFlags(ex=True, lb=True, vs=True)),
        VisitSpec(visitnum=7, visit="WEEK 3", nominal_day=21, window_lower=-2, window_upper=2, epoch="TREATMENT",
                 collection_flags=CollectionFlags(ex=True, lb=True, vs=True)),
        VisitSpec(visitnum=8, visit="WEEK 4", nominal_day=28, window_lower=-2, window_upper=2, epoch="TREATMENT",
                 collection_flags=CollectionFlags(ex=True, lb=True, vs=True, ecg=True)),
        VisitSpec(visitnum=9, visit="WEEK 6", nominal_day=42, window_lower=-2, window_upper=2, epoch="TREATMENT",
                 collection_flags=CollectionFlags(ex=True, lb=True, vs=True)),
        VisitSpec(visitnum=10, visit="WEEK 8/EOT", nominal_day=56, window_lower=-2, window_upper=2, epoch="TREATMENT",
                 collection_flags=CollectionFlags(ex=True, lb=True, vs=True, ecg=True)),
        VisitSpec(visitnum=11, visit="WEEK 10", nominal_day=70, window_lower=-3, window_upper=3, epoch="FOLLOW-UP",
                 collection_flags=CollectionFlags(lb=True, vs=True, ex=False)),
        VisitSpec(visitnum=12, visit="WEEK 12", nominal_day=84, window_lower=-7, window_upper=7, epoch="FOLLOW-UP",
                 collection_flags=CollectionFlags(lb=True, vs=True, ex=False)),
        VisitSpec(visitnum=13, visit="MONTH 4", nominal_day=120, window_lower=-7, window_upper=7, epoch="FOLLOW-UP",
                 collection_flags=CollectionFlags(lb=True, vs=True, ex=False)),
        VisitSpec(visitnum=14, visit="MONTH 6", nominal_day=180, window_lower=-7, window_upper=7, epoch="FOLLOW-UP",
                 collection_flags=CollectionFlags(lb=True, vs=True, ex=False)),
        VisitSpec(visitnum=15, visit="MONTH 12", nominal_day=365, window_lower=-14, window_upper=14, epoch="FOLLOW-UP",
                 collection_flags=CollectionFlags(lb=True, vs=True, ex=False)),
    ]
    
    ts_params = [
        TSParameter(tsparmcd="STUDYID", tsval="DNDi-CH-E1224-003"),
        TSParameter(tsparmcd="TITLE", tsval="BENDITA - Benznidazole New Doses Improved Treatment Chagas"),
        TSParameter(tsparmcd="TPHASE", tsval="Phase 2"),
        TSParameter(tsparmcd="THERAREA", tsval="Infectious Disease"),
        TSParameter(tsparmcd="STYPE", tsval="INTERVENTIONAL"),
        TSParameter(tsparmcd="RANDOM", tsval="Y"),
    ]
    
    return TrialDesignSpec(
        study_id="DNDi-CH-E1224-003",
        title="BENDITA - Benznidazole New Doses Improved Treatment Chagas",
        phase="2",
        therapeutic_area="Infectious Disease",
        n_subjects_default=210,
        arms=arms,
        elements=elements,
        arm_paths=arm_paths,
        visits=visits,
        ts_parameters=ts_params,
    )


class ProtocolSpecExtractor:
    """Extracts trial design specifications from protocol identifiers."""
    
    SUPPORTED_PROTOCOLS = {
        # BENDITA - Chagas Disease
        "bendita": "DNDi-CH-E1224-003",
        "dndi-ch-e1224-003": "DNDi-CH-E1224-003",
        "chagas": "DNDi-CH-E1224-003",
        # HS-11-421 - Opioid Use Disorder
        "hs11421": "HS-11-421",
        "hs-11-421": "HS-11-421",
        "opioid": "HS-11-421",
        # TJ301 - Ulcerative Colitis
        "tj301": "CTJ301UC201",
        "ctj301uc201": "CTJ301UC201",
        "olamkicept": "CTJ301UC201",
        "ulcerative": "CTJ301UC201",
        # HERALD - COVID-19 Vaccine
        "herald": "CV-NCOV-004",
        "cv-ncov-004": "CV-NCOV-004",
        "cvncov004": "CV-NCOV-004",
        "cvncov": "CV-NCOV-004",
        "covid": "CV-NCOV-004",
        # PROTECT - Type 1 Diabetes
        "protect": "PRV-031-001",
        "prv-031-001": "PRV-031-001",
        "prv031001": "PRV-031-001",
        "teplizumab": "PRV-031-001",
        "t1d": "PRV-031-001",
        # LTS17352 - Cold Agglutinin Disease
        "lts17352": "LTS17352",
        "sutimlimab": "LTS17352",
        "cad": "LTS17352",
    }
    
    def __init__(self, protocol_id: str):
        self.protocol_id = protocol_id.lower().replace("_", "-").replace(" ", "")
        self.assumptions: List[Assumption] = []
    
    def extract(self) -> TrialDesignSpec:
        """Extract the trial design specification for the given protocol."""
        # BENDITA
        if self.protocol_id in ("bendita", "dndi-ch-e1224-003", "chagas"):
            spec = extract_bendita_spec()
            self.assumptions = [
                Assumption(source="extractor", parameter="visits", 
                          assumed_value="derived from protocol",
                          reason="Visit windows derived from protocol schedule"),
            ]
            return spec
        # HS-11-421
        elif self.protocol_id in ("hs11421", "hs-11-421", "opioid"):
            spec = extract_hs11421_spec()
            self.assumptions = [
                Assumption(source="extractor", parameter="visits",
                          assumed_value="weekly then monthly",
                          reason="Weekly visits for Phase 1, monthly for Phase 2"),
            ]
            return spec
        # TJ301
        elif self.protocol_id in ("tj301", "ctj301uc201", "olamkicept", "ulcerative"):
            spec = extract_tj301_spec()
            self.assumptions = [
                Assumption(source="extractor", parameter="visits",
                          assumed_value="Q2W dosing schedule",
                          reason="IV infusion every 2 weeks for 12 weeks"),
            ]
            return spec
        # HERALD
        elif self.protocol_id in ("herald", "cv-ncov-004", "cvncov004", "cvncov", "covid"):
            spec = extract_herald_spec()
            self.assumptions = [
                Assumption(source="extractor", parameter="design",
                          assumed_value="1:1 randomization, observer-blind",
                          reason="Vaccine vs placebo, 2 doses 28 days apart"),
            ]
            return spec
        # PROTECT
        elif self.protocol_id in ("protect", "prv-031-001", "prv031001", "teplizumab", "t1d"):
            spec = extract_protect_spec()
            self.assumptions = [
                Assumption(source="extractor", parameter="design",
                          assumed_value="2:1 randomization, double-blind",
                          reason="Two 12-day IV infusion courses"),
            ]
            return spec
        # LTS17352
        elif self.protocol_id in ("lts17352", "sutimlimab", "cad"):
            spec = extract_lts17352_spec()
            self.assumptions = [
                Assumption(source="extractor", parameter="design",
                          assumed_value="Open-label extension",
                          reason="Q2W IV infusion continuation study"),
            ]
            return spec
        # BDA (AV005) - 2×2 crossover, EIB
        elif self.protocol_id in ("bda", "av005", "tyree"):
            spec = extract_bda_spec()
            self.assumptions = [
                Assumption(source="extractor", parameter="design",
                          assumed_value="2×2 Crossover",
                          reason="Single-dose per period, 7-day washout"),
            ]
            return spec
        # USL261 (P261-402) - parallel, seizure clusters
        elif self.protocol_id in ("usl261", "p261-402", "artemis"):
            spec = extract_usl261_spec()
            self.assumptions = [
                Assumption(source="extractor", parameter="design",
                          assumed_value="Open-label extension",
                          reason="Event-driven dosing, single-arm safety study"),
            ]
            return spec
        # KONFIDENT (KVD900-301) - 3-way crossover, HAE
        elif self.protocol_id in ("konfident", "kvd900-301", "kvd900"):
            spec = extract_konfident_spec()
            self.assumptions = [
                Assumption(source="extractor", parameter="design",
                          assumed_value="3-way Crossover",
                          reason="6 sequences, attack-driven dosing, 48h washout"),
            ]
            return spec
        else:
            supported = ['bendita', 'hs11421', 'tj301', 'herald', 'protect', 'lts17352',
                         'bda', 'usl261', 'konfident']
            raise ValueError(f"Unknown protocol: {self.protocol_id}. Supported: {supported}")
    
    def get_assumptions(self) -> List[Assumption]:
        """Return assumptions made during extraction."""
        return self.assumptions
    
    @classmethod
    def list_protocols(cls) -> list:
        """List main protocol identifiers."""
        return ['bendita', 'hs11421', 'tj301', 'herald', 'protect', 'lts17352']


def extract_hs11421_spec() -> TrialDesignSpec:
    """
    Create specification for HS-11-421 trial (Opioid dependence, Phase 3).
    
    CAM2038 (buprenorphine depot) vs sublingual buprenorphine
    
    Design:
    - Phase 1 (Week 1-12): Weekly visits, weekly CAM2038 q1w injections
    - Phase 2 (Week 13-24): Monthly visits, monthly CAM2038 q4w injections  
    - Follow-up (Week 25-29)
    
    Treatment arms:
    - Group 1 (SLBPN): SL BPN daily + Placebo SC injections
    - Group 2 (CAM203): CAM2038 SC injections + SL Placebo daily
    
    Note: Injections are clinic-administered (one per visit), SL is daily take-home.
    Regimen mode='visit' generates one EX record per scheduled visit.
    Regimen mode='daily' (default) generates period records.
    """
    arms = [
        ArmSpec(armcd="SLBPN", arm="SL BPN + Placebo SC", regimen=[
            # Daily sublingual - period mode (default)
            RegimenItem(extrt="BUPRENORPHINE", dose=16, dose_unit="mg", route=Route.SUBLINGUAL, 
                       frequency=DoseFrequency.QD, mode="daily"),
            # Weekly placebo injection - visit mode (one record per injection visit)
            RegimenItem(extrt="PLACEBO SC", dose=0, dose_unit="mL", route=Route.SUBCUTANEOUS, 
                       frequency=DoseFrequency.QW, mode="visit")
        ]),
        ArmSpec(armcd="CAM203", arm="CAM2038 SC + Placebo SL", regimen=[
            # Weekly CAM2038 injection during Phase 1 - visit mode
            RegimenItem(extrt="CAM2038 Q1W", dose=24, dose_unit="mg", route=Route.SUBCUTANEOUS, 
                       frequency=DoseFrequency.QW, mode="visit", element_ref="PHASE1"),
            # Monthly CAM2038 injection during Phase 2 - visit mode  
            RegimenItem(extrt="CAM2038 Q4W", dose=128, dose_unit="mg", route=Route.SUBCUTANEOUS, 
                       frequency=DoseFrequency.Q4W, mode="visit", element_ref="PHASE2"),
            # Daily placebo sublingual - period mode
            RegimenItem(extrt="PLACEBO SL", dose=0, dose_unit="mg", route=Route.SUBLINGUAL, 
                       frequency=DoseFrequency.QD, mode="daily")
        ]),
    ]
    
    elements = [
        ElementSpec(etcd="SCRN", element="Screening", epoch="SCREENING", nominal_duration_days=21,
                   start_rule="Informed consent", end_rule="Before Day 1"),
        ElementSpec(etcd="PHASE1", element="Phase 1 - Weekly", epoch="TREATMENT", nominal_duration_days=84,
                   start_rule="Day 1", end_rule="Week 12"),
        ElementSpec(etcd="PHASE2", element="Phase 2 - Monthly", epoch="TREATMENT", nominal_duration_days=84,
                   start_rule="Week 13", end_rule="Week 24"),
        ElementSpec(etcd="FU", element="Follow-up", epoch="FOLLOW-UP", nominal_duration_days=28,
                   start_rule="End of treatment", end_rule="Week 29"),
    ]
    
    arm_paths = [ArmPath(armcd=arm.armcd, elements=[
        ArmPathItem(etcd="SCRN", taetord=1),
        ArmPathItem(etcd="PHASE1", taetord=2),
        ArmPathItem(etcd="PHASE2", taetord=3),
        ArmPathItem(etcd="FU", taetord=4),
    ]) for arm in arms]
    
    visits = [
        # Screening
        VisitSpec(visitnum=1, visit="SCREENING", nominal_day=-10, window_lower=-11, window_upper=11, epoch="SCREENING",
                 collection_flags=CollectionFlags(mh=True, lb=True, vs=True, pe=True, ex=False)),
        
        # Phase 1: Week 1 (Day 1, 2, 4) + weekly visits Week 2-12
        VisitSpec(visitnum=2, visit="DAY 1/WEEK 1", nominal_day=1, window_lower=0, window_upper=0, epoch="TREATMENT",
                 collection_flags=CollectionFlags(ex=True, lb=True, vs=True, ecg=True)),
        VisitSpec(visitnum=3, visit="DAY 2", nominal_day=2, window_lower=0, window_upper=0, epoch="TREATMENT",
                 collection_flags=CollectionFlags(ex=True, vs=True, lb=False)),
        VisitSpec(visitnum=4, visit="DAY 4", nominal_day=4, window_lower=-1, window_upper=1, epoch="TREATMENT",
                 collection_flags=CollectionFlags(ex=True, vs=True, lb=False)),
        VisitSpec(visitnum=5, visit="DAY 8/WEEK 2", nominal_day=8, window_lower=-2, window_upper=2, epoch="TREATMENT",
                 collection_flags=CollectionFlags(ex=True, lb=True, vs=True)),
    ]
    
    # Weekly visits for weeks 3-12 (±2 days)
    for week in range(3, 13):
        visits.append(VisitSpec(
            visitnum=week + 3,  # 6-15
            visit=f"WEEK {week}",
            nominal_day=week * 7,
            window_lower=-2,
            window_upper=2,
            epoch="TREATMENT",
            collection_flags=CollectionFlags(ex=True, lb=(week % 2 == 0), vs=True, ecg=(week % 4 == 0))
        ))
    
    # Phase 2: Monthly visits at Week 13, 17, 21, 24/EOT (±7 days)
    # Week 13 is transition from q1w to q4w
    visits.append(VisitSpec(
        visitnum=16, visit="WEEK 13", nominal_day=91, window_lower=-2, window_upper=2, epoch="TREATMENT",
        collection_flags=CollectionFlags(ex=True, lb=True, vs=True, ecg=True)
    ))
    
    for i, week in enumerate([17, 21], start=1):
        visits.append(VisitSpec(
            visitnum=16 + i,
            visit=f"WEEK {week}",
            nominal_day=week * 7,
            window_lower=-7,
            window_upper=7,
            epoch="TREATMENT",
            collection_flags=CollectionFlags(ex=True, lb=True, vs=True, ecg=True)
        ))
    
    # Week 24/25 - End of Treatment
    visits.append(VisitSpec(
        visitnum=19, visit="WEEK 24/EOT", nominal_day=168, window_lower=-7, window_upper=7, epoch="TREATMENT",
        collection_flags=CollectionFlags(ex=False, lb=True, vs=True, ecg=True, pe=True)
    ))
    
    # Follow-up: Week 29
    visits.append(VisitSpec(
        visitnum=20,
        visit="WEEK 29/FOLLOW-UP",
        nominal_day=203,
        window_lower=-7,
        window_upper=7,
        epoch="FOLLOW-UP",
        collection_flags=CollectionFlags(lb=True, vs=True, pe=True, ex=False)
    ))
    
    ts_params = [
        TSParameter(tsparmcd="STUDYID", tsval="HS-11-421"),
        TSParameter(tsparmcd="TITLE", tsval="CAM2038 vs Sublingual Buprenorphine for Opioid Use Disorder"),
        TSParameter(tsparmcd="TPHASE", tsval="Phase 3"),
        TSParameter(tsparmcd="THERAREA", tsval="CNS/Psychiatry"),
        TSParameter(tsparmcd="STYPE", tsval="INTERVENTIONAL"),
        TSParameter(tsparmcd="RANDOM", tsval="Y"),
    ]
    
    return TrialDesignSpec(
        study_id="HS-11-421",
        title="CAM2038 vs Sublingual Buprenorphine for Opioid Use Disorder",
        phase="3",
        therapeutic_area="CNS/Psychiatry",
        n_subjects_default=428,
        arms=arms,
        elements=elements,
        arm_paths=arm_paths,
        visits=visits,
        ts_parameters=ts_params,
    )


def extract_tj301_spec() -> TrialDesignSpec:
    """
    Create specification for TJ301/CTJ301UC201 trial (Ulcerative Colitis, Phase 2).
    
    Protocol: A Phase II, Randomized, Double-blind, Placebo-controlled Study to Evaluate
    the Safety and Efficacy of TJ301 (Olamkicept) Administered Intravenously in
    Patients with Active Ulcerative Colitis
    
    Sponsor: Leading Biopharm Limited
    90 patients, 1:1:1 randomization across 3 arms
    12-week treatment period + 3-week safety follow-up
    """
    # Treatment Arms: TJ301 600mg Q2W, TJ301 300mg Q2W, Placebo Q2W
    # Dosing on Days 0, 14, 28, 42, 56, 70 per protocol Table 1
    arms = [
        ArmSpec(armcd="TJ600", arm="TJ301 600mg Q2W", regimen=[
            RegimenItem(extrt="TJ301", dose=600, dose_unit="mg", route=Route.INTRAVENOUS, 
                       frequency=DoseFrequency.Q2W, mode="visit")
        ]),
        ArmSpec(armcd="TJ300", arm="TJ301 300mg Q2W", regimen=[
            RegimenItem(extrt="TJ301", dose=300, dose_unit="mg", route=Route.INTRAVENOUS, 
                       frequency=DoseFrequency.Q2W, mode="visit")
        ]),
        ArmSpec(armcd="PBO", arm="Placebo Q2W", regimen=[
            RegimenItem(extrt="PLACEBO", dose=0, dose_unit="mg", route=Route.INTRAVENOUS, 
                       frequency=DoseFrequency.Q2W, mode="visit")
        ]),
    ]
    
    # Trial Elements
    elements = [
        ElementSpec(etcd="SCRN", element="Screening", epoch="SCREENING", nominal_duration_days=28,
                   start_rule="Informed consent", end_rule="Day -1 before randomization"),
        ElementSpec(etcd="TRT", element="Treatment", epoch="TREATMENT", nominal_duration_days=84,
                   start_rule="Randomization (Day 0)", end_rule="End of treatment (Week 12)"),
        ElementSpec(etcd="FU", element="Follow-up", epoch="FOLLOW-UP", nominal_duration_days=21,
                   start_rule="End of treatment", end_rule="Safety follow-up (Day 105)"),
    ]
    
    # Arm paths - all arms follow same path
    arm_paths = [ArmPath(armcd=arm.armcd, elements=[
        ArmPathItem(etcd="SCRN", taetord=1),
        ArmPathItem(etcd="TRT", taetord=2),
        ArmPathItem(etcd="FU", taetord=3),
    ]) for arm in arms]
    
    # Visit Schedule per protocol CTJ301UC201 Table 1
    # Protocol uses Day 0 for first dose; SDTM uses Day 1 as reference
    # Protocol Day 0 → SDTM Day 1, Protocol Day 14 → SDTM Day 15, etc.
    visits = [
        # Screening Period (Days -28 to -1 prior to Baseline)
        VisitSpec(visitnum=1, visit="SCREENING", nominal_day=-14, window_lower=-28, window_upper=0, 
                 epoch="SCREENING",
                 collection_flags=CollectionFlags(mh=True, lb=True, vs=True, ecg=True, pe=True, ex=False)),
        
        # Baseline/Randomization (Protocol Day 0 = SDTM Day 1) - First dose
        VisitSpec(visitnum=2, visit="BASELINE", nominal_day=1, window_lower=0, window_upper=0, 
                 epoch="TREATMENT",
                 collection_flags=CollectionFlags(lb=True, vs=True, ecg=True, ex=True, ae=True)),
        
        # Treatment Period - Q2W dosing per protocol
        # Protocol Day 14 = SDTM Day 15
        VisitSpec(visitnum=3, visit="WEEK 2", nominal_day=15, window_lower=-1, window_upper=1, 
                 epoch="TREATMENT",
                 collection_flags=CollectionFlags(lb=True, vs=True, ex=True, ae=True)),
        
        # Protocol Day 28 = SDTM Day 29
        VisitSpec(visitnum=4, visit="WEEK 4", nominal_day=29, window_lower=-2, window_upper=2, 
                 epoch="TREATMENT",
                 collection_flags=CollectionFlags(lb=True, vs=True, ecg=True, ex=True, ae=True)),
        
        # Protocol Day 42 = SDTM Day 43
        VisitSpec(visitnum=5, visit="WEEK 6", nominal_day=43, window_lower=-2, window_upper=2, 
                 epoch="TREATMENT",
                 collection_flags=CollectionFlags(lb=True, vs=True, ex=True, ae=True)),
        
        # Protocol Day 56 = SDTM Day 57
        VisitSpec(visitnum=6, visit="WEEK 8", nominal_day=57, window_lower=-2, window_upper=2, 
                 epoch="TREATMENT",
                 collection_flags=CollectionFlags(lb=True, vs=True, ecg=True, ex=True, ae=True)),
        
        # Protocol Day 70 = SDTM Day 71 (last dose)
        VisitSpec(visitnum=7, visit="WEEK 10", nominal_day=71, window_lower=-2, window_upper=2, 
                 epoch="TREATMENT",
                 collection_flags=CollectionFlags(lb=True, vs=True, ex=True, ae=True)),
        
        # End of Treatment (Protocol Day 84 = SDTM Day 85) - No dosing
        VisitSpec(visitnum=8, visit="WEEK 12/EOT", nominal_day=85, window_lower=-2, window_upper=2, 
                 epoch="TREATMENT",
                 collection_flags=CollectionFlags(lb=True, vs=True, ecg=True, pe=True, ae=True, ex=False)),
        
        # Safety Follow-up (Protocol Day 105 = SDTM Day 106) - No dosing
        VisitSpec(visitnum=9, visit="FOLLOW-UP", nominal_day=106, window_lower=-7, window_upper=7, 
                 epoch="FOLLOW-UP",
                 collection_flags=CollectionFlags(lb=True, vs=True, ae=True, ex=False)),
    ]
    
    ts_params = [
        TSParameter(tsparmcd="STUDYID", tsval="CTJ301UC201"),
        TSParameter(tsparmcd="TITLE", tsval="TJ301 (Olamkicept) Phase II in Active Ulcerative Colitis"),
        TSParameter(tsparmcd="TPHASE", tsval="Phase 2"),
        TSParameter(tsparmcd="THERAREA", tsval="Gastroenterology"),
        TSParameter(tsparmcd="STYPE", tsval="INTERVENTIONAL"),
        TSParameter(tsparmcd="RANDOM", tsval="Y"),
        TSParameter(tsparmcd="SDESIGN", tsval="PARALLEL"),
        TSParameter(tsparmcd="INDIC", tsval="ULCERATIVE COLITIS"),
        TSParameter(tsparmcd="TRT", tsval="TJ301 (OLAMKICEPT)"),
        TSParameter(tsparmcd="ROUTE", tsval="INTRAVENOUS"),
        TSParameter(tsparmcd="REGIMEN", tsval="Q2W"),
    ]
    
    return TrialDesignSpec(
        study_id="CTJ301UC201",
        title="TJ301 (Olamkicept) Phase II in Active Ulcerative Colitis",
        phase="2",
        therapeutic_area="Gastroenterology",
        n_subjects_default=90,
        arms=arms,
        elements=elements,
        arm_paths=arm_paths,
        visits=visits,
        ts_parameters=ts_params,
        demographics=DemographicsDefaults(
            age_min=18,
            age_max=70,
            age_mean=42,
            age_sd=12,
            sex_distribution={'M': 0.55, 'F': 0.45},
            race_distribution={
                'ASIAN': 0.70,
                'WHITE': 0.20,
                'OTHER': 0.10
            },
            ethnic_distribution={
                'NOT HISPANIC OR LATINO': 0.98,
                'UNKNOWN': 0.02
            },
            country='CHN',
            total_subjects=90,
            subjects_per_arm={'TJ600': 30, 'TJ300': 30, 'PBO': 30},
            n_sites=10,
        ),
        ae_model=AEModelDefaults(
            ae_term_library=[
                # Ulcerative Colitis and IL-6 inhibitor-specific AEs
                AETermProfile(aeterm="ULCERATIVE COLITIS FLARE", aedecod="Ulcerative colitis",
                             aebodsys="GASTROINTESTINAL DISORDERS", weight=2.5),
                AETermProfile(aeterm="ABDOMINAL PAIN", aedecod="Abdominal pain",
                             aebodsys="GASTROINTESTINAL DISORDERS", weight=3.0),
                AETermProfile(aeterm="DIARRHEA", aedecod="Diarrhoea",
                             aebodsys="GASTROINTESTINAL DISORDERS", weight=2.5),
                AETermProfile(aeterm="RECTAL HEMORRHAGE", aedecod="Rectal haemorrhage",
                             aebodsys="GASTROINTESTINAL DISORDERS", weight=2.0),
                AETermProfile(aeterm="NAUSEA", aedecod="Nausea",
                             aebodsys="GASTROINTESTINAL DISORDERS", weight=2.0),
                AETermProfile(aeterm="INFUSION RELATED REACTION", aedecod="Infusion related reaction",
                             aebodsys="INJURY, POISONING AND PROCEDURAL COMPLICATIONS", weight=1.5),
                AETermProfile(aeterm="UPPER RESPIRATORY TRACT INFECTION", aedecod="Upper respiratory tract infection",
                             aebodsys="INFECTIONS AND INFESTATIONS", weight=2.0),
                AETermProfile(aeterm="NASOPHARYNGITIS", aedecod="Nasopharyngitis",
                             aebodsys="INFECTIONS AND INFESTATIONS", weight=1.5),
                AETermProfile(aeterm="HEADACHE", aedecod="Headache",
                             aebodsys="NERVOUS SYSTEM DISORDERS", weight=1.5),
                AETermProfile(aeterm="ARTHRALGIA", aedecod="Arthralgia",
                             aebodsys="MUSCULOSKELETAL AND CONNECTIVE TISSUE DISORDERS", weight=1.5),
            ]
        ),
    )


def extract_herald_spec() -> TrialDesignSpec:
    """
    Create specification for HERALD trial (CV-NCOV-004).
    COVID-19 mRNA vaccine CVnCoV, Phase 2b/3.
    Sponsor: CureVac AG
    """
    arms = [
        ArmSpec(armcd="VACCINE", arm="CVnCoV 12µg", regimen=[
            RegimenItem(extrt="CVnCoV", dose=12, dose_unit="µg", 
                       route=Route.INTRAMUSCULAR, frequency=DoseFrequency.Q4W,
                       mode="visit")  # 2 doses: Day 1, Day 29
        ]),
        ArmSpec(armcd="PBO", arm="Placebo (Saline)", regimen=[
            RegimenItem(extrt="PLACEBO", dose=0, dose_unit="mL", 
                       route=Route.INTRAMUSCULAR, frequency=DoseFrequency.Q4W,
                       mode="visit")
        ]),
    ]
    
    elements = [
        ElementSpec(etcd="SCRN", element="Screening", epoch="SCREENING", nominal_duration_days=14),
        ElementSpec(etcd="VAC", element="Vaccination", epoch="TREATMENT", nominal_duration_days=29),
        ElementSpec(etcd="FU", element="Follow-up", epoch="FOLLOW-UP", nominal_duration_days=365),
    ]
    
    arm_paths = [ArmPath(armcd=arm.armcd, elements=[
        ArmPathItem(etcd="SCRN", taetord=1),
        ArmPathItem(etcd="VAC", taetord=2),
        ArmPathItem(etcd="FU", taetord=3),
    ]) for arm in arms]
    
    visits = [
        VisitSpec(visitnum=1, visit="SCREENING", nominal_day=-7, window_lower=-7, window_upper=0,
                 epoch="SCREENING", collection_flags=CollectionFlags(mh=True, lb=True, vs=True)),
        VisitSpec(visitnum=2, visit="DAY 1 (DOSE 1)", nominal_day=1, window_lower=0, window_upper=0,
                 epoch="TREATMENT", collection_flags=CollectionFlags(vs=True, ex=True, ae=True)),
        VisitSpec(visitnum=3, visit="DAY 29 (DOSE 2)", nominal_day=29, window_lower=-3, window_upper=3,
                 epoch="TREATMENT", collection_flags=CollectionFlags(vs=True, ex=True, ae=True)),
        VisitSpec(visitnum=4, visit="DAY 43", nominal_day=43, window_lower=-3, window_upper=3,
                 epoch="FOLLOW-UP", collection_flags=CollectionFlags(vs=True, lb=True, ae=True)),
        VisitSpec(visitnum=5, visit="DAY 57", nominal_day=57, window_lower=-7, window_upper=7,
                 epoch="FOLLOW-UP", collection_flags=CollectionFlags(vs=True, ae=True)),
        VisitSpec(visitnum=6, visit="DAY 120", nominal_day=120, window_lower=-14, window_upper=14,
                 epoch="FOLLOW-UP", collection_flags=CollectionFlags(vs=True, lb=True, ae=True)),
        VisitSpec(visitnum=7, visit="DAY 211", nominal_day=211, window_lower=-14, window_upper=14,
                 epoch="FOLLOW-UP", collection_flags=CollectionFlags(vs=True, lb=True, ae=True)),
        VisitSpec(visitnum=8, visit="DAY 393 (END)", nominal_day=393, window_lower=-14, window_upper=14,
                 epoch="FOLLOW-UP", collection_flags=CollectionFlags(vs=True, lb=True, ae=True)),
    ]
    
    ts_params = [
        TSParameter(tsparmcd="STUDYID", tsval="CV-NCOV-004"),
        TSParameter(tsparmcd="TITLE", tsval="HERALD: Efficacy and Safety of CVnCoV mRNA COVID-19 Vaccine"),
        TSParameter(tsparmcd="TPHASE", tsval="Phase 2b/3"),
        TSParameter(tsparmcd="SPONSOR", tsval="CureVac AG"),
        TSParameter(tsparmcd="THERAREA", tsval="Infectious Disease"),
        TSParameter(tsparmcd="STYPE", tsval="INTERVENTIONAL"),
        TSParameter(tsparmcd="RANDOM", tsval="Y"),
        TSParameter(tsparmcd="SDESIGN", tsval="PARALLEL"),
        TSParameter(tsparmcd="TBLIND", tsval="SINGLE BLIND"),
        TSParameter(tsparmcd="INDIC", tsval="COVID-19"),
        TSParameter(tsparmcd="TRT", tsval="CVnCoV mRNA Vaccine"),
        TSParameter(tsparmcd="ROUTE", tsval="INTRAMUSCULAR"),
    ]
    
    assumptions = [
        Assumption(parameter="ENROLLMENT", assumed_value="36500", 
                  reason="Target from protocol - generating sample"),
        Assumption(parameter="RANDOMIZATION", assumed_value="1:1",
                  reason="Equal allocation to vaccine vs placebo"),
    ]
    
    return TrialDesignSpec(
        study_id="CV-NCOV-004",
        title="HERALD: Efficacy and Safety of CVnCoV mRNA COVID-19 Vaccine",
        phase="2b/3",
        therapeutic_area="Infectious Disease",
        n_subjects_default=500,  # Sample size for generation
        arms=arms,
        elements=elements,
        arm_paths=arm_paths,
        visits=visits,
        ts_parameters=ts_params,
        assumptions=assumptions,
    )


def extract_protect_spec() -> TrialDesignSpec:
    """
    Create specification for PROTECT trial (PRV-031-001).
    Teplizumab for Type 1 Diabetes in children/adolescents.
    Sponsor: Provention Bio
    """
    arms = [
        ArmSpec(armcd="TEPL", arm="Teplizumab", regimen=[
            RegimenItem(extrt="TEPLIZUMAB", dose=51, dose_unit="µg/m2", 
                       route=Route.INTRAVENOUS, frequency=DoseFrequency.QD,
                       mode="visit")  # 12-day IV infusion courses
        ]),
        ArmSpec(armcd="PBO", arm="Placebo", regimen=[
            RegimenItem(extrt="PLACEBO", dose=0, dose_unit="mL", 
                       route=Route.INTRAVENOUS, frequency=DoseFrequency.QD,
                       mode="visit")
        ]),
    ]
    
    elements = [
        ElementSpec(etcd="SCRN", element="Screening", epoch="SCREENING", nominal_duration_days=42),
        ElementSpec(etcd="TRT1", element="Treatment Course 1", epoch="TREATMENT", nominal_duration_days=12),
        ElementSpec(etcd="OBS1", element="Observation 1", epoch="TREATMENT", nominal_duration_days=170),
        ElementSpec(etcd="TRT2", element="Treatment Course 2", epoch="TREATMENT", nominal_duration_days=12),
        ElementSpec(etcd="FU", element="Follow-up", epoch="FOLLOW-UP", nominal_duration_days=365),
    ]
    
    arm_paths = [ArmPath(armcd=arm.armcd, elements=[
        ArmPathItem(etcd="SCRN", taetord=1),
        ArmPathItem(etcd="TRT1", taetord=2),
        ArmPathItem(etcd="OBS1", taetord=3),
        ArmPathItem(etcd="TRT2", taetord=4),
        ArmPathItem(etcd="FU", taetord=5),
    ]) for arm in arms]
    
    # PROTECT visit schedule per protocol PRV-031-001 v4.0
    # Screening up to 6 weeks, Course 1 (Days 1-12), Course 2 (Days 182-193), Follow-up to Week 78
    visits = [
        # Screening (up to 6 weeks before Day 1)
        VisitSpec(visitnum=1, visit="SCREENING", nominal_day=-42, window_lower=-42, window_upper=0,
                 epoch="SCREENING", collection_flags=CollectionFlags(mh=True, lb=True, vs=True, pe=True)),
        
        # Course 1: 12 daily IV infusions (Days 1-12)
        VisitSpec(visitnum=2, visit="DAY 1 (COURSE 1 START)", nominal_day=1, window_lower=0, window_upper=0,
                 epoch="TREATMENT", collection_flags=CollectionFlags(vs=True, ex=True, lb=True)),
        VisitSpec(visitnum=3, visit="DAY 12 (COURSE 1 END)", nominal_day=12, window_lower=0, window_upper=0,
                 epoch="TREATMENT", collection_flags=CollectionFlags(vs=True, ex=True, lb=True, ae=True)),
        
        # Observation period between courses
        VisitSpec(visitnum=4, visit="WEEK 4", nominal_day=28, window_lower=-3, window_upper=3,
                 epoch="TREATMENT", collection_flags=CollectionFlags(vs=True, lb=True, ae=True)),
        VisitSpec(visitnum=5, visit="WEEK 12", nominal_day=84, window_lower=-7, window_upper=7,
                 epoch="TREATMENT", collection_flags=CollectionFlags(vs=True, lb=True, ae=True)),
        VisitSpec(visitnum=6, visit="WEEK 20", nominal_day=140, window_lower=-7, window_upper=7,
                 epoch="TREATMENT", collection_flags=CollectionFlags(vs=True, lb=True, ae=True)),
        
        # Course 2: 12 daily IV infusions (Days 182-193)
        VisitSpec(visitnum=7, visit="WEEK 26 (COURSE 2 START)", nominal_day=182, window_lower=-7, window_upper=7,
                 epoch="TREATMENT", collection_flags=CollectionFlags(vs=True, ex=True, lb=True)),
        VisitSpec(visitnum=8, visit="DAY 193 (COURSE 2 END)", nominal_day=193, window_lower=0, window_upper=0,
                 epoch="TREATMENT", collection_flags=CollectionFlags(vs=True, ex=True, lb=True, ae=True)),
        
        # Post-treatment follow-up
        VisitSpec(visitnum=9, visit="WEEK 30", nominal_day=210, window_lower=-7, window_upper=7,
                 epoch="FOLLOW-UP", collection_flags=CollectionFlags(vs=True, lb=True, ae=True)),
        VisitSpec(visitnum=10, visit="WEEK 34", nominal_day=238, window_lower=-7, window_upper=7,
                 epoch="FOLLOW-UP", collection_flags=CollectionFlags(vs=True, lb=True, ae=True)),
        VisitSpec(visitnum=11, visit="WEEK 39", nominal_day=273, window_lower=-7, window_upper=7,
                 epoch="FOLLOW-UP", collection_flags=CollectionFlags(vs=True, lb=True, ae=True)),
        VisitSpec(visitnum=12, visit="WEEK 52", nominal_day=364, window_lower=-7, window_upper=7,
                 epoch="FOLLOW-UP", collection_flags=CollectionFlags(vs=True, lb=True, ae=True)),
        VisitSpec(visitnum=13, visit="WEEK 65", nominal_day=455, window_lower=-7, window_upper=7,
                 epoch="FOLLOW-UP", collection_flags=CollectionFlags(vs=True, lb=True, ae=True)),
        VisitSpec(visitnum=14, visit="WEEK 78 (END OF STUDY)", nominal_day=546, window_lower=-14, window_upper=14,
                 epoch="FOLLOW-UP", collection_flags=CollectionFlags(vs=True, lb=True, ae=True, pe=True)),
    ]
    
    ts_params = [
        TSParameter(tsparmcd="STUDYID", tsval="PRV-031-001"),
        TSParameter(tsparmcd="TITLE", tsval="PROTECT: Teplizumab in Newly Diagnosed Type 1 Diabetes"),
        TSParameter(tsparmcd="TPHASE", tsval="Phase 3"),
        TSParameter(tsparmcd="SPONSOR", tsval="Provention Bio"),
        TSParameter(tsparmcd="THERAREA", tsval="Endocrinology"),
        TSParameter(tsparmcd="STYPE", tsval="INTERVENTIONAL"),
        TSParameter(tsparmcd="RANDOM", tsval="Y"),
        TSParameter(tsparmcd="SDESIGN", tsval="PARALLEL"),
        TSParameter(tsparmcd="TBLIND", tsval="DOUBLE BLIND"),
        TSParameter(tsparmcd="INDIC", tsval="TYPE 1 DIABETES"),
        TSParameter(tsparmcd="TRT", tsval="TEPLIZUMAB"),
        TSParameter(tsparmcd="ROUTE", tsval="INTRAVENOUS"),
        TSParameter(tsparmcd="AGEMIN", tsval="8"),
        TSParameter(tsparmcd="AGEMAX", tsval="17"),
    ]
    
    assumptions = [
        Assumption(parameter="ENROLLMENT", assumed_value="300", 
                  reason="Target 200 teplizumab + 100 placebo"),
        Assumption(parameter="RANDOMIZATION", assumed_value="2:1",
                  reason="2:1 allocation teplizumab:placebo"),
        Assumption(parameter="POPULATION", assumed_value="Pediatric",
                  reason="Children and adolescents 8-17 years"),
    ]
    
    return TrialDesignSpec(
        study_id="PRV-031-001",
        title="PROTECT: Teplizumab in Newly Diagnosed Type 1 Diabetes",
        phase="3",
        therapeutic_area="Endocrinology",
        n_subjects_default=300,
        arms=arms,
        elements=elements,
        arm_paths=arm_paths,
        visits=visits,
        ts_parameters=ts_params,
        assumptions=assumptions,
        demographics=DemographicsDefaults(
            age_min=8,
            age_max=17,
            age_mean=12.5,
            age_sd=2.5,
            sex_distribution={'M': 0.52, 'F': 0.48},
            race_distribution={
                'WHITE': 0.75,
                'BLACK OR AFRICAN AMERICAN': 0.10,
                'ASIAN': 0.05,
                'OTHER': 0.10
            },
            ethnic_distribution={
                'NOT HISPANIC OR LATINO': 0.85,
                'HISPANIC OR LATINO': 0.12,
                'UNKNOWN': 0.03
            },
            country='USA',
            total_subjects=300,
            subjects_per_arm={'TEPL': 200, 'PBO': 100},
        ),
        ae_model=AEModelDefaults(
            ae_term_library=[
                # Type 1 Diabetes and Teplizumab-specific AEs
                AETermProfile(aeterm="HYPOGLYCEMIA", aedecod="Hypoglycaemia", 
                             aebodsys="METABOLISM AND NUTRITION DISORDERS", weight=3.0),
                AETermProfile(aeterm="INJECTION SITE REACTION", aedecod="Injection site reaction",
                             aebodsys="GENERAL DISORDERS AND ADMINISTRATION SITE CONDITIONS", weight=2.5),
                AETermProfile(aeterm="LYMPHOPENIA", aedecod="Lymphopenia",
                             aebodsys="BLOOD AND LYMPHATIC SYSTEM DISORDERS", weight=2.0),
                AETermProfile(aeterm="CYTOKINE RELEASE SYNDROME", aedecod="Cytokine release syndrome",
                             aebodsys="IMMUNE SYSTEM DISORDERS", weight=1.5),
                AETermProfile(aeterm="RASH", aedecod="Rash",
                             aebodsys="SKIN AND SUBCUTANEOUS TISSUE DISORDERS", weight=2.0),
                AETermProfile(aeterm="HEADACHE", aedecod="Headache",
                             aebodsys="NERVOUS SYSTEM DISORDERS", weight=2.0),
                AETermProfile(aeterm="NAUSEA", aedecod="Nausea",
                             aebodsys="GASTROINTESTINAL DISORDERS", weight=1.5),
                AETermProfile(aeterm="FATIGUE", aedecod="Fatigue",
                             aebodsys="GENERAL DISORDERS AND ADMINISTRATION SITE CONDITIONS", weight=1.5),
                AETermProfile(aeterm="PYREXIA", aedecod="Pyrexia",
                             aebodsys="GENERAL DISORDERS AND ADMINISTRATION SITE CONDITIONS", weight=1.5),
                AETermProfile(aeterm="UPPER RESPIRATORY TRACT INFECTION", aedecod="Upper respiratory tract infection",
                             aebodsys="INFECTIONS AND INFESTATIONS", weight=2.0),
            ]
        ),
    )


def extract_lts17352_spec() -> TrialDesignSpec:
    """
    Create specification for LTS17352 trial.
    Sutimlimab open-label extension for Cold Agglutinin Disease.
    Sponsor: Sanofi
    """
    arms = [
        ArmSpec(armcd="SUTI", arm="Sutimlimab", regimen=[
            RegimenItem(extrt="SUTIMLIMAB", dose=6500, dose_unit="mg", 
                       route=Route.INTRAVENOUS, frequency=DoseFrequency.Q2W,
                       mode="visit")
        ]),
    ]
    
    elements = [
        ElementSpec(etcd="ENROLL", element="Enrollment", epoch="SCREENING", nominal_duration_days=7),
        ElementSpec(etcd="TRT", element="Treatment", epoch="TREATMENT", nominal_duration_days=365),
    ]
    
    arm_paths = [ArmPath(armcd="SUTI", elements=[
        ArmPathItem(etcd="ENROLL", taetord=1),
        ArmPathItem(etcd="TRT", taetord=2),
    ])]
    
    # Visit Schedule per protocol LTS17352 Schedule of Activities
    # Protocol uses Day 0 for first dose; SDTM uses Day 1 as reference
    # Protocol Day 0 → SDTM Day 1, Protocol Day 7 → SDTM Day 8, etc.
    visits = [
        # Day 0: Baseline with first infusion (Protocol Day 0 = SDTM Day 1)
        VisitSpec(visitnum=1, visit="DAY 0 (BASELINE)", nominal_day=1, window_lower=0, window_upper=0,
                 epoch="SCREENING", collection_flags=CollectionFlags(mh=True, lb=True, vs=True, ex=True)),
        
        # Day 7: Second loading dose (Protocol Day 7 = SDTM Day 8, ±2 days window)
        VisitSpec(visitnum=2, visit="DAY 7", nominal_day=8, window_lower=-2, window_upper=2,
                 epoch="TREATMENT", collection_flags=CollectionFlags(vs=True, ex=True, lb=True, ae=True)),
        
        # Day 21: Third dose (Protocol Day 21 = SDTM Day 22, ±2 days window)
        VisitSpec(visitnum=3, visit="DAY 21", nominal_day=22, window_lower=-2, window_upper=2,
                 epoch="TREATMENT", collection_flags=CollectionFlags(vs=True, ex=True, lb=True, ae=True)),
        
        # Q2W dosing continues (every 2 weeks after Day 21)
        # Protocol Day 35 = SDTM Day 36
        VisitSpec(visitnum=4, visit="WEEK 5", nominal_day=36, window_lower=-14, window_upper=14,
                 epoch="TREATMENT", collection_flags=CollectionFlags(vs=True, ex=True, ae=True)),
        # Protocol Day 49 = SDTM Day 50
        VisitSpec(visitnum=5, visit="WEEK 7", nominal_day=50, window_lower=-14, window_upper=14,
                 epoch="TREATMENT", collection_flags=CollectionFlags(vs=True, ex=True, ae=True)),
        # Protocol Day 63 = SDTM Day 64
        VisitSpec(visitnum=6, visit="WEEK 9", nominal_day=64, window_lower=-14, window_upper=14,
                 epoch="TREATMENT", collection_flags=CollectionFlags(vs=True, ex=True, ae=True)),
        # Protocol Day 77 = SDTM Day 78
        VisitSpec(visitnum=7, visit="WEEK 11", nominal_day=78, window_lower=-14, window_upper=14,
                 epoch="TREATMENT", collection_flags=CollectionFlags(vs=True, ex=True, ae=True)),
        # Protocol Day 91 = SDTM Day 92
        VisitSpec(visitnum=8, visit="WEEK 13", nominal_day=92, window_lower=-14, window_upper=14,
                 epoch="TREATMENT", collection_flags=CollectionFlags(vs=True, ex=True, lb=True, ae=True)),
        
        # Quarterly assessments (every 3 months per protocol)
        # Protocol Day 182 = SDTM Day 183
        VisitSpec(visitnum=9, visit="WEEK 26", nominal_day=183, window_lower=-14, window_upper=14,
                 epoch="TREATMENT", collection_flags=CollectionFlags(vs=True, ex=True, lb=True, ae=True)),
        # Protocol Day 273 = SDTM Day 274
        VisitSpec(visitnum=10, visit="WEEK 39", nominal_day=274, window_lower=-14, window_upper=14,
                 epoch="TREATMENT", collection_flags=CollectionFlags(vs=True, ex=True, lb=True, ae=True)),
        # Protocol Day 364 = SDTM Day 365
        VisitSpec(visitnum=11, visit="WEEK 52", nominal_day=365, window_lower=-14, window_upper=14,
                 epoch="TREATMENT", collection_flags=CollectionFlags(vs=True, ex=True, lb=True, ae=True, pe=True)),
        
        # Safety follow-up (9 weeks after last dose per protocol) - No dosing
        VisitSpec(visitnum=12, visit="SAFETY FOLLOW-UP", nominal_day=428, window_lower=-14, window_upper=14,
                 epoch="FOLLOW-UP", collection_flags=CollectionFlags(vs=True, lb=True, ae=True, ex=False)),
    ]
    
    ts_params = [
        TSParameter(tsparmcd="STUDYID", tsval="LTS17352"),
        TSParameter(tsparmcd="TITLE", tsval="Sutimlimab Open-Label Extension in Cold Agglutinin Disease"),
        TSParameter(tsparmcd="TPHASE", tsval="Phase 3"),
        TSParameter(tsparmcd="SPONSOR", tsval="Sanofi"),
        TSParameter(tsparmcd="THERAREA", tsval="Hematology"),
        TSParameter(tsparmcd="STYPE", tsval="INTERVENTIONAL"),
        TSParameter(tsparmcd="RANDOM", tsval="N"),
        TSParameter(tsparmcd="SDESIGN", tsval="SINGLE GROUP"),
        TSParameter(tsparmcd="TBLIND", tsval="OPEN LABEL"),
        TSParameter(tsparmcd="INDIC", tsval="COLD AGGLUTININ DISEASE"),
        TSParameter(tsparmcd="TRT", tsval="SUTIMLIMAB"),
        TSParameter(tsparmcd="ROUTE", tsval="INTRAVENOUS"),
    ]
    
    return TrialDesignSpec(
        study_id="LTS17352",
        title="Sutimlimab Open-Label Extension in Cold Agglutinin Disease",
        phase="3",
        therapeutic_area="Hematology",
        n_subjects_default=50,
        arms=arms,
        elements=elements,
        arm_paths=arm_paths,
        visits=visits,
        ts_parameters=ts_params,
        demographics=DemographicsDefaults(
            age_min=18,
            age_max=85,
            age_mean=68,
            age_sd=10,
            sex_distribution={'M': 0.40, 'F': 0.60},  # CAD more common in women
            race_distribution={'ASIAN': 1.0},  # Japan-only study
            ethnic_distribution={'NOT HISPANIC OR LATINO': 1.0},
            country='JPN',
            total_subjects=50,
            subjects_per_arm={'SUTI': 50},
            n_sites=3,
            sites=['TOKYO01', 'OSAKA01', 'NAGOYA01'],
        ),
        ae_model=AEModelDefaults(
            ae_term_library=[
                # Cold Agglutinin Disease and Complement inhibitor-specific AEs
                AETermProfile(aeterm="HEMOLYSIS", aedecod="Haemolysis",
                             aebodsys="BLOOD AND LYMPHATIC SYSTEM DISORDERS", weight=2.5),
                AETermProfile(aeterm="ANEMIA", aedecod="Anaemia",
                             aebodsys="BLOOD AND LYMPHATIC SYSTEM DISORDERS", weight=2.0),
                AETermProfile(aeterm="ACROCYANOSIS", aedecod="Acrocyanosis",
                             aebodsys="VASCULAR DISORDERS", weight=2.0),
                AETermProfile(aeterm="INFUSION RELATED REACTION", aedecod="Infusion related reaction",
                             aebodsys="INJURY, POISONING AND PROCEDURAL COMPLICATIONS", weight=2.0),
                AETermProfile(aeterm="HEADACHE", aedecod="Headache",
                             aebodsys="NERVOUS SYSTEM DISORDERS", weight=2.0),
                AETermProfile(aeterm="HYPERTENSION", aedecod="Hypertension",
                             aebodsys="VASCULAR DISORDERS", weight=1.5),
                AETermProfile(aeterm="FATIGUE", aedecod="Fatigue",
                             aebodsys="GENERAL DISORDERS AND ADMINISTRATION SITE CONDITIONS", weight=2.0),
                AETermProfile(aeterm="DIARRHEA", aedecod="Diarrhoea",
                             aebodsys="GASTROINTESTINAL DISORDERS", weight=1.5),
                AETermProfile(aeterm="UPPER RESPIRATORY TRACT INFECTION", aedecod="Upper respiratory tract infection",
                             aebodsys="INFECTIONS AND INFESTATIONS", weight=2.0),
                AETermProfile(aeterm="NASOPHARYNGITIS", aedecod="Nasopharyngitis",
                             aebodsys="INFECTIONS AND INFESTATIONS", weight=1.5),
            ]
        ),
    )


# ─── Phase 2: New Protocol Spec Extractors ───────────────────────────────────

def extract_bda_spec() -> TrialDesignSpec:
    """
    Create specification for BDA trial (AV005 / TYREE).
    2×2 Crossover, Single-Dose Per Period, Exercise-Induced Bronchoconstriction.
    """
    arms = [
        ArmSpec(armcd="BDA_MDI", arm="BDA MDI 160/180 mcg", regimen=[
            RegimenItem(extrt="BDA MDI 160/180 MCG", dose=160, dose_unit="mcg",
                       route=Route.INHALATION, frequency=DoseFrequency.ONCE,
                       dosage_form="METERED DOSE INHALER")
        ]),
        ArmSpec(armcd="PLACEBO", arm="Placebo MDI", regimen=[
            RegimenItem(extrt="PLACEBO MDI", dose=0, dose_unit="mcg",
                       route=Route.INHALATION, frequency=DoseFrequency.ONCE,
                       dosage_form="METERED DOSE INHALER")
        ]),
    ]

    elements = [
        ElementSpec(etcd="SCRN", element="Screening", epoch="SCREENING", nominal_duration_days=14),
        ElementSpec(etcd="EIB", element="EIB Confirmation", epoch="SCREENING", nominal_duration_days=7),
        ElementSpec(etcd="PRD1", element="Treatment Period 1", epoch="PERIOD 1", nominal_duration_days=1),
        ElementSpec(etcd="WASH", element="Washout", epoch="WASHOUT", nominal_duration_days=6),
        ElementSpec(etcd="PRD2", element="Treatment Period 2", epoch="PERIOD 2", nominal_duration_days=1),
        ElementSpec(etcd="FU", element="Follow-up", epoch="FOLLOW-UP", nominal_duration_days=4),
    ]

    arm_paths = [
        ArmPath(armcd="AB", elements=[
            ArmPathItem(etcd="SCRN", taetord=1), ArmPathItem(etcd="EIB", taetord=2),
            ArmPathItem(etcd="PRD1", taetord=3), ArmPathItem(etcd="WASH", taetord=4),
            ArmPathItem(etcd="PRD2", taetord=5), ArmPathItem(etcd="FU", taetord=6),
        ]),
        ArmPath(armcd="BA", elements=[
            ArmPathItem(etcd="SCRN", taetord=1), ArmPathItem(etcd="EIB", taetord=2),
            ArmPathItem(etcd="PRD1", taetord=3), ArmPathItem(etcd="WASH", taetord=4),
            ArmPathItem(etcd="PRD2", taetord=5), ArmPathItem(etcd="FU", taetord=6),
        ]),
    ]

    visits = [
        VisitSpec(visitnum=1, visit="SCREENING (V1)", nominal_day=-14, window_lower=0, window_upper=7,
                 epoch="SCREENING", collection_flags=CollectionFlags(mh=True, vs=True, lb=True)),
        VisitSpec(visitnum=2, visit="EIB CONFIRMATION (V2)", nominal_day=-7, window_lower=-3, window_upper=3,
                 epoch="SCREENING", collection_flags=CollectionFlags(vs=True, lb=True)),
        VisitSpec(visitnum=3, visit="PERIOD 1 (V3)", nominal_day=1, window_lower=0, window_upper=0,
                 epoch="PERIOD 1", collection_flags=CollectionFlags(vs=True, ex=True)),
        VisitSpec(visitnum=4, visit="PERIOD 2 (V4)", nominal_day=8, window_lower=-2, window_upper=2,
                 epoch="PERIOD 2", collection_flags=CollectionFlags(vs=True, ex=True)),
        VisitSpec(visitnum=5, visit="FOLLOW-UP (TC)", nominal_day=12, window_lower=0, window_upper=2,
                 epoch="FOLLOW-UP", collection_flags=CollectionFlags(vs=True)),
    ]

    crossover_sequences = [
        {'seqcd': 'AB', 'label': 'Sequence AB: BDA then Placebo',
         'periods': [
             {'period': 1, 'armcd': 'BDA_MDI', 'epoch': 'PERIOD 1',
              'start_day': 1, 'end_day': 1, 'washout_days_before': 0},
             {'period': 2, 'armcd': 'PLACEBO', 'epoch': 'PERIOD 2',
              'start_day': 8, 'end_day': 8, 'washout_days_before': 7},
         ]},
        {'seqcd': 'BA', 'label': 'Sequence BA: Placebo then BDA',
         'periods': [
             {'period': 1, 'armcd': 'PLACEBO', 'epoch': 'PERIOD 1',
              'start_day': 1, 'end_day': 1, 'washout_days_before': 0},
             {'period': 2, 'armcd': 'BDA_MDI', 'epoch': 'PERIOD 2',
              'start_day': 8, 'end_day': 8, 'washout_days_before': 7},
         ]},
    ]

    ts_params = [
        TSParameter(tsparmcd="STUDYID", tsval="AV005"),
        TSParameter(tsparmcd="TITLE", tsval="TYREE: BDA MDI vs Placebo on Exercise-Induced Bronchoconstriction"),
        TSParameter(tsparmcd="TPHASE", tsval="Phase 3"),
        TSParameter(tsparmcd="SPONSOR", tsval="Bond Avillion 2 Development LP"),
        TSParameter(tsparmcd="THERAREA", tsval="Respiratory"),
        TSParameter(tsparmcd="STYPE", tsval="INTERVENTIONAL"),
        TSParameter(tsparmcd="RANDOM", tsval="Y"),
        TSParameter(tsparmcd="SDESIGN", tsval="CROSSOVER"),
        TSParameter(tsparmcd="TBLIND", tsval="DOUBLE BLIND"),
        TSParameter(tsparmcd="INDIC", tsval="EXERCISE-INDUCED BRONCHOCONSTRICTION"),
    ]

    return TrialDesignSpec(
        study_id="AV005",
        title="TYREE: BDA MDI vs Placebo on Exercise-Induced Bronchoconstriction",
        phase="3",
        therapeutic_area="Respiratory",
        n_subjects_default=60,
        arms=arms,
        elements=elements,
        arm_paths=arm_paths,
        visits=visits,
        ts_parameters=ts_params,
        is_crossover=True,
        crossover_sequences=crossover_sequences,
        total_study_days=12,
        arm_order=["AB", "BA"],
        allow_low_shaped_exposure_probability=True,
        demographics=DemographicsDefaults(
            age_min=12, age_max=70, age_mean=35, age_sd=14,
            sex_distribution={'M': 0.45, 'F': 0.55},
            race_distribution={'WHITE': 0.70, 'BLACK OR AFRICAN AMERICAN': 0.15,
                               'ASIAN': 0.08, 'OTHER': 0.07},
            country='USA', n_sites=6,
            sites=['SITE001', 'SITE002', 'SITE003', 'SITE004', 'SITE005', 'SITE006'],
            total_subjects=60,
            subjects_per_arm={'AB': 30, 'BA': 30},
        ),
        disposition_model=DispositionModelDefaults(screen_fail_rate=0.50, completion_rate=0.95),
        ae_model=AEModelDefaults(
            ae_rate_multiplier=0.3,  # Short exposure → fewer AEs
            time_shape_params=(1.0, 1.0),  # Uniform (very short study)
            pool_size=30,
        ),
    )


def extract_usl261_spec() -> TrialDesignSpec:
    """
    Create specification for USL261 trial (P261-402 / ARTEMIS Extension).
    Open-label, single-arm safety extension, event-driven (seizure cluster) dosing.
    Intranasal Midazolam.
    """
    arms = [
        ArmSpec(armcd="USL261", arm="USL261 5mg Intranasal", regimen=[
            RegimenItem(extrt="USL261 5 MG", dose=5.0, dose_unit="mg",
                       route=Route.NASAL, frequency=DoseFrequency.PRN,
                       dosage_form="SPRAY")
        ]),
    ]

    elements = [
        ElementSpec(etcd="ENROLL", element="Enrollment", epoch="SCREENING", nominal_duration_days=1),
        ElementSpec(etcd="TRT", element="Treatment", epoch="TREATMENT", nominal_duration_days=365),
        ElementSpec(etcd="FU", element="Follow-up", epoch="FOLLOW-UP", nominal_duration_days=84),
    ]

    arm_paths = [ArmPath(armcd="USL261", elements=[
        ArmPathItem(etcd="ENROLL", taetord=1),
        ArmPathItem(etcd="TRT", taetord=2),
        ArmPathItem(etcd="FU", taetord=3),
    ])]

    visits = [
        VisitSpec(visitnum=1, visit="VISIT 1 (ENROLLMENT)", nominal_day=1,
                 epoch="SCREENING", collection_flags=CollectionFlags(mh=True, lb=True, vs=True)),
        VisitSpec(visitnum=2, visit="VISIT 2", nominal_day=90, window_lower=-5, window_upper=5,
                 epoch="TREATMENT", collection_flags=CollectionFlags(lb=True, vs=True)),
        VisitSpec(visitnum=3, visit="VISIT 3", nominal_day=180, window_lower=-14, window_upper=14,
                 epoch="TREATMENT", collection_flags=CollectionFlags(lb=True, vs=True)),
        VisitSpec(visitnum=4, visit="VISIT 4", nominal_day=270, window_lower=-14, window_upper=14,
                 epoch="TREATMENT", collection_flags=CollectionFlags(lb=True, vs=True)),
        VisitSpec(visitnum=5, visit="VISIT 5", nominal_day=365, window_lower=-14, window_upper=14,
                 epoch="TREATMENT", collection_flags=CollectionFlags(lb=True, vs=True)),
        VisitSpec(visitnum=6, visit="FINAL VISIT", nominal_day=450, window_lower=-14, window_upper=28,
                 epoch="FOLLOW-UP", collection_flags=CollectionFlags(lb=True, vs=True)),
    ]

    ts_params = [
        TSParameter(tsparmcd="STUDYID", tsval="P261-402"),
        TSParameter(tsparmcd="TITLE", tsval="Open-Label Safety Study of USL261 in Seizure Clusters"),
        TSParameter(tsparmcd="TPHASE", tsval="Phase 3"),
        TSParameter(tsparmcd="SPONSOR", tsval="Upsher-Smith Laboratories"),
        TSParameter(tsparmcd="THERAREA", tsval="Neurology"),
        TSParameter(tsparmcd="STYPE", tsval="INTERVENTIONAL"),
        TSParameter(tsparmcd="RANDOM", tsval="N"),
        TSParameter(tsparmcd="SDESIGN", tsval="SINGLE GROUP"),
        TSParameter(tsparmcd="TBLIND", tsval="OPEN LABEL"),
        TSParameter(tsparmcd="INDIC", tsval="SEIZURE CLUSTERS"),
    ]

    return TrialDesignSpec(
        study_id="P261-402",
        title="Open-Label Safety Study of USL261 in Seizure Clusters",
        phase="3",
        therapeutic_area="Neurology",
        n_subjects_default=240,
        arms=arms,
        elements=elements,
        arm_paths=arm_paths,
        visits=visits,
        ts_parameters=ts_params,
        total_study_days=450,
        arm_order=["USL261"],
        demographics=DemographicsDefaults(
            age_min=12, age_max=85, age_mean=40, age_sd=18,
            sex_distribution={'M': 0.48, 'F': 0.52},
            race_distribution={'WHITE': 0.72, 'BLACK OR AFRICAN AMERICAN': 0.12,
                               'ASIAN': 0.06, 'OTHER': 0.10},
            country='USA', n_sites=30,
            sites=['SITE' + str(i).zfill(3) for i in range(1, 31)],
            total_subjects=240,
            subjects_per_arm={'USL261': 240},
        ),
        disposition_model=DispositionModelDefaults(screen_fail_rate=0.05, completion_rate=0.80),
        ae_model=AEModelDefaults(ae_rate_multiplier=1.2),
    )


def extract_konfident_spec() -> TrialDesignSpec:
    """
    Create specification for KONFIDENT trial (KVD900-301).
    3-way Crossover, 6 sequences, on-demand HAE attack treatment.
    """
    arms = [
        ArmSpec(armcd="KVD900_600MG", arm="KVD900 600mg", regimen=[
            RegimenItem(extrt="KVD900 600 MG", dose=600, dose_unit="mg",
                       route=Route.ORAL, frequency=DoseFrequency.PRN,
                       dosage_form="TABLET, FILM COATED")
        ]),
        ArmSpec(armcd="KVD900_300MG", arm="KVD900 300mg", regimen=[
            RegimenItem(extrt="KVD900 300 MG", dose=300, dose_unit="mg",
                       route=Route.ORAL, frequency=DoseFrequency.PRN,
                       dosage_form="TABLET, FILM COATED")
        ]),
        ArmSpec(armcd="PLACEBO", arm="Placebo", regimen=[
            RegimenItem(extrt="PLACEBO", dose=0, dose_unit="mg",
                       route=Route.ORAL, frequency=DoseFrequency.PRN,
                       dosage_form="TABLET")
        ]),
    ]

    elements = [
        ElementSpec(etcd="SCRN", element="Screening", epoch="SCREENING", nominal_duration_days=28),
        ElementSpec(etcd="PRD1", element="Treatment Period 1", epoch="PERIOD 1", nominal_duration_days=42),
        ElementSpec(etcd="WO1", element="Washout 1", epoch="WASHOUT 1", nominal_duration_days=2),
        ElementSpec(etcd="PRD2", element="Treatment Period 2", epoch="PERIOD 2", nominal_duration_days=42),
        ElementSpec(etcd="WO2", element="Washout 2", epoch="WASHOUT 2", nominal_duration_days=2),
        ElementSpec(etcd="PRD3", element="Treatment Period 3", epoch="PERIOD 3", nominal_duration_days=42),
        ElementSpec(etcd="FU", element="Follow-up", epoch="FOLLOW-UP", nominal_duration_days=45),
    ]

    # All 6 sequences share the same element path structure
    seq_codes = ["ABC", "ACB", "BAC", "BCA", "CAB", "CBA"]
    arm_paths = [ArmPath(armcd=sc, elements=[
        ArmPathItem(etcd="SCRN", taetord=1),
        ArmPathItem(etcd="PRD1", taetord=2), ArmPathItem(etcd="WO1", taetord=3),
        ArmPathItem(etcd="PRD2", taetord=4), ArmPathItem(etcd="WO2", taetord=5),
        ArmPathItem(etcd="PRD3", taetord=6), ArmPathItem(etcd="FU", taetord=7),
    ]) for sc in seq_codes]

    visits = [
        VisitSpec(visitnum=1, visit="SCREENING", nominal_day=-28, window_lower=0, window_upper=14,
                 epoch="SCREENING", collection_flags=CollectionFlags(mh=True, lb=True, vs=True)),
        VisitSpec(visitnum=2, visit="RANDOMIZATION", nominal_day=1, window_lower=0, window_upper=0,
                 epoch="PERIOD 1", collection_flags=CollectionFlags(lb=True, vs=True)),
        VisitSpec(visitnum=3, visit="POST-ATTACK 1 TELEVISIT", nominal_day=45,
                 window_lower=-14, window_upper=14,
                 epoch="PERIOD 1", collection_flags=CollectionFlags(vs=True)),
        VisitSpec(visitnum=4, visit="POST-ATTACK 2 TELEVISIT", nominal_day=90,
                 window_lower=-14, window_upper=14,
                 epoch="PERIOD 2", collection_flags=CollectionFlags(vs=True)),
        VisitSpec(visitnum=5, visit="POST-ATTACK 3 TELEVISIT", nominal_day=135,
                 window_lower=-14, window_upper=14,
                 epoch="PERIOD 3", collection_flags=CollectionFlags(vs=True)),
        VisitSpec(visitnum=6, visit="FINAL VISIT", nominal_day=175, window_lower=-14, window_upper=14,
                 epoch="FOLLOW-UP", collection_flags=CollectionFlags(lb=True, vs=True)),
    ]

    # 3-way crossover: A=600mg, B=300mg, C=Placebo
    crossover_sequences = [
        {'seqcd': 'ABC', 'label': 'Sequence ABC: 600mg then 300mg then Placebo', 'periods': [
            {'period': 1, 'armcd': 'KVD900_600MG', 'epoch': 'PERIOD 1', 'start_day': 1, 'end_day': 42, 'washout_days_before': 0},
            {'period': 2, 'armcd': 'KVD900_300MG', 'epoch': 'PERIOD 2', 'start_day': 44, 'end_day': 86, 'washout_days_before': 2},
            {'period': 3, 'armcd': 'PLACEBO', 'epoch': 'PERIOD 3', 'start_day': 88, 'end_day': 130, 'washout_days_before': 2},
        ]},
        {'seqcd': 'ACB', 'label': 'Sequence ACB: 600mg then Placebo then 300mg', 'periods': [
            {'period': 1, 'armcd': 'KVD900_600MG', 'epoch': 'PERIOD 1', 'start_day': 1, 'end_day': 42, 'washout_days_before': 0},
            {'period': 2, 'armcd': 'PLACEBO', 'epoch': 'PERIOD 2', 'start_day': 44, 'end_day': 86, 'washout_days_before': 2},
            {'period': 3, 'armcd': 'KVD900_300MG', 'epoch': 'PERIOD 3', 'start_day': 88, 'end_day': 130, 'washout_days_before': 2},
        ]},
        {'seqcd': 'BAC', 'label': 'Sequence BAC: 300mg then 600mg then Placebo', 'periods': [
            {'period': 1, 'armcd': 'KVD900_300MG', 'epoch': 'PERIOD 1', 'start_day': 1, 'end_day': 42, 'washout_days_before': 0},
            {'period': 2, 'armcd': 'KVD900_600MG', 'epoch': 'PERIOD 2', 'start_day': 44, 'end_day': 86, 'washout_days_before': 2},
            {'period': 3, 'armcd': 'PLACEBO', 'epoch': 'PERIOD 3', 'start_day': 88, 'end_day': 130, 'washout_days_before': 2},
        ]},
        {'seqcd': 'BCA', 'label': 'Sequence BCA: 300mg then Placebo then 600mg', 'periods': [
            {'period': 1, 'armcd': 'KVD900_300MG', 'epoch': 'PERIOD 1', 'start_day': 1, 'end_day': 42, 'washout_days_before': 0},
            {'period': 2, 'armcd': 'PLACEBO', 'epoch': 'PERIOD 2', 'start_day': 44, 'end_day': 86, 'washout_days_before': 2},
            {'period': 3, 'armcd': 'KVD900_600MG', 'epoch': 'PERIOD 3', 'start_day': 88, 'end_day': 130, 'washout_days_before': 2},
        ]},
        {'seqcd': 'CAB', 'label': 'Sequence CAB: Placebo then 600mg then 300mg', 'periods': [
            {'period': 1, 'armcd': 'PLACEBO', 'epoch': 'PERIOD 1', 'start_day': 1, 'end_day': 42, 'washout_days_before': 0},
            {'period': 2, 'armcd': 'KVD900_600MG', 'epoch': 'PERIOD 2', 'start_day': 44, 'end_day': 86, 'washout_days_before': 2},
            {'period': 3, 'armcd': 'KVD900_300MG', 'epoch': 'PERIOD 3', 'start_day': 88, 'end_day': 130, 'washout_days_before': 2},
        ]},
        {'seqcd': 'CBA', 'label': 'Sequence CBA: Placebo then 300mg then 600mg', 'periods': [
            {'period': 1, 'armcd': 'PLACEBO', 'epoch': 'PERIOD 1', 'start_day': 1, 'end_day': 42, 'washout_days_before': 0},
            {'period': 2, 'armcd': 'KVD900_300MG', 'epoch': 'PERIOD 2', 'start_day': 44, 'end_day': 86, 'washout_days_before': 2},
            {'period': 3, 'armcd': 'KVD900_600MG', 'epoch': 'PERIOD 3', 'start_day': 88, 'end_day': 130, 'washout_days_before': 2},
        ]},
    ]

    ts_params = [
        TSParameter(tsparmcd="STUDYID", tsval="KVD900-301"),
        TSParameter(tsparmcd="TITLE", tsval="KONFIDENT: KVD900 for On-Demand Treatment of HAE Attacks"),
        TSParameter(tsparmcd="TPHASE", tsval="Phase 3"),
        TSParameter(tsparmcd="SPONSOR", tsval="KalVista Pharmaceuticals"),
        TSParameter(tsparmcd="THERAREA", tsval="Immunology"),
        TSParameter(tsparmcd="STYPE", tsval="INTERVENTIONAL"),
        TSParameter(tsparmcd="RANDOM", tsval="Y"),
        TSParameter(tsparmcd="SDESIGN", tsval="CROSSOVER"),
        TSParameter(tsparmcd="TBLIND", tsval="DOUBLE BLIND"),
        TSParameter(tsparmcd="INDIC", tsval="HEREDITARY ANGIOEDEMA"),
    ]

    return TrialDesignSpec(
        study_id="KVD900-301",
        title="KONFIDENT: KVD900 for On-Demand Treatment of HAE Attacks",
        phase="3",
        therapeutic_area="Immunology",
        n_subjects_default=90,
        arms=arms,
        elements=elements,
        arm_paths=arm_paths,
        visits=visits,
        ts_parameters=ts_params,
        is_crossover=True,
        crossover_sequences=crossover_sequences,
        total_study_days=175,
        arm_order=["ABC", "ACB", "BAC", "BCA", "CAB", "CBA"],
        demographics=DemographicsDefaults(
            age_min=12, age_max=75, age_mean=38, age_sd=14,
            sex_distribution={'M': 0.40, 'F': 0.60},
            race_distribution={'WHITE': 0.75, 'BLACK OR AFRICAN AMERICAN': 0.08,
                               'ASIAN': 0.10, 'OTHER': 0.07},
            country='USA', n_sites=20,
            sites=['SITE' + str(i).zfill(3) for i in range(1, 21)],
            total_subjects=90,
            subjects_per_arm={'ABC': 15, 'ACB': 15, 'BAC': 15,
                              'BCA': 15, 'CAB': 15, 'CBA': 15},
        ),
        disposition_model=DispositionModelDefaults(screen_fail_rate=0.10, completion_rate=0.85),
        ae_model=AEModelDefaults(ae_rate_multiplier=0.8),
    )

