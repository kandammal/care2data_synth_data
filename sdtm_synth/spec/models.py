"""
Pydantic models for Trial Design Specification.
"""

from __future__ import annotations
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, field_validator
from datetime import date
from enum import Enum


class DoseFrequency(str, Enum):
    QD = "QD"
    BID = "BID"
    TID = "TID"
    QID = "QID"
    QW = "QW"
    Q2W = "Q2W"
    Q4W = "Q4W"
    PRN = "PRN"
    ONCE = "ONCE"
    CONTINUOUS = "CONTINUOUS"


class Route(str, Enum):
    ORAL = "ORAL"
    SUBCUTANEOUS = "SUBCUTANEOUS"
    INTRAVENOUS = "INTRAVENOUS"
    INTRAMUSCULAR = "INTRAMUSCULAR"
    TOPICAL = "TOPICAL"
    SUBLINGUAL = "SUBLINGUAL"
    INHALATION = "INHALATION"
    NASAL = "NASAL"
    UNKNOWN = "UNKNOWN"


class RegimenItem(BaseModel):
    """
    Specification for a treatment regimen within an arm.
    
    mode: Determines how EX records are generated
        - 'daily': One EX record covering the entire dosing period (default)
        - 'visit': One EX record per scheduled visit where treatment is administered
                   (appropriate for clinic-administered injections)
    """
    extrt: str = Field(..., description="Exposure treatment name")
    dose: float = Field(..., ge=0)
    dose_unit: str = Field(default="mg")
    route: Route = Field(default=Route.ORAL)
    frequency: DoseFrequency = Field(default=DoseFrequency.QD)
    start_rule: str = Field(default="Start of element")
    end_rule: str = Field(default="End of element")
    element_ref: Optional[str] = None
    mode: str = Field(default="daily", description="EX record mode: 'daily' or 'visit'")
    dosage_form: str = Field(default="", description="Dosage form e.g., TABLET, INJECTION")


class ArmSpec(BaseModel):
    armcd: str = Field(..., max_length=20)
    arm: str
    description: Optional[str] = None
    regimen: List[RegimenItem] = Field(default_factory=list)
    
    @field_validator('armcd')
    @classmethod
    def armcd_upper(cls, v: str) -> str:
        return v.upper()[:20]


class ElementSpec(BaseModel):
    etcd: str = Field(..., max_length=8)
    element: str
    start_rule: str = ""
    end_rule: str = ""
    nominal_duration_days: int = Field(default=1, ge=0)
    epoch: str
    
    @field_validator('etcd')
    @classmethod
    def etcd_upper(cls, v: str) -> str:
        return v.upper()[:8]


class ArmPathItem(BaseModel):
    etcd: str
    taetord: int = Field(..., ge=1)


class ArmPath(BaseModel):
    armcd: str
    elements: List[ArmPathItem] = Field(default_factory=list)


class CollectionFlags(BaseModel):
    """Flags indicating which assessments are collected at a visit."""
    vs: bool = True   # Vital Signs
    lb: bool = True   # Labs
    ae: bool = True   # Adverse Events
    ex: bool = False  # Exposure (only True for dosing visits)
    cm: bool = True   # Concomitant Meds
    mh: bool = False  # Medical History (usually only at screening)
    ecg: bool = False # ECG
    pe: bool = False  # Physical Exam


class VisitSpec(BaseModel):
    visitnum: float
    visit: str
    nominal_day: int
    window_lower: int = 0
    window_upper: int = 0
    epoch: Optional[str] = None
    collection_flags: CollectionFlags = Field(default_factory=CollectionFlags)
    expand_rule: Optional[str] = None
    tvstrl: str = ""
    tvenrl: str = ""
    armcd: Optional[str] = None


class DispositionModelDefaults(BaseModel):
    screen_fail_rate: float = Field(default=0.1, ge=0, le=1)
    completion_rate: float = Field(default=0.85, ge=0, le=1)
    dropout_rate_by_epoch: Dict[str, float] = Field(default_factory=dict)
    # Note: DEATH is excluded by default for clean SDTM generation
    # (avoids DS death without corresponding FATAL AE)
    # Add "DEATH" to enable death outcomes (requires AE generator non-clean mode)
    ds_categories: List[str] = Field(default_factory=lambda: [
        "COMPLETED", "ADVERSE EVENT", "LOST TO FOLLOW-UP",
        "WITHDRAWAL BY SUBJECT", "PROTOCOL VIOLATION", "PHYSICIAN DECISION"
    ])


class AETermProfile(BaseModel):
    """An AE term with its relative frequency in this indication."""
    aeterm: str
    aedecod: str
    aebodsys: str
    weight: float = Field(default=1.0, ge=0, description="Relative frequency weight")


class AEModelDefaults(BaseModel):
    """AE generation parameters - spec-driven distributions."""
    # Overall AE rate multiplier (1.0 = default rate)
    ae_rate_multiplier: float = Field(default=1.0, ge=0)
    
    # Protocol-specific AE term library
    # If empty, uses generic defaults
    ae_term_library: List[AETermProfile] = Field(default_factory=list)
    
    # Relationship distribution - per CDISC SDTM CT codelist C66768
    relationship_dist: Dict[str, float] = Field(default_factory=lambda: {
        'NOT RELATED': 0.40,
        'UNLIKELY RELATED': 0.20,
        'POSSIBLY RELATED': 0.25,
        'PROBABLY RELATED': 0.10,
        'RELATED': 0.05,
    })
    
    # Outcome distribution - per CDISC SDTM CT codelist AEOUT
    outcome_dist: Dict[str, float] = Field(default_factory=lambda: {
        'RECOVERED/RESOLVED': 0.72,
        'RECOVERING/RESOLVING': 0.15,
        'NOT RECOVERED/NOT RESOLVED': 0.10,
        'RECOVERED/RESOLVED WITH SEQUELAE': 0.02,
        'UNKNOWN': 0.01,
    })
    
    # Enable FATAL outcomes (requires corresponding DS death records)
    enable_fatal: bool = Field(default=False)
    
    # v2: Beta distribution time-shaping params for AE clustering (§2.2.1)
    # (1.0, 1.0) = uniform (no shaping); (1.5, 3.0) = early clustering
    time_shape_params: tuple = Field(default=(1.0, 1.0))
    
    # v2: AE candidate pool size (0 = auto-compute from protocol)
    pool_size: int = Field(default=0, ge=0)
    
    # v2: Death rate for fatal AE generation
    death_rate: float = Field(default=0.02, ge=0, le=1)
    
    # v2: Cached at spec-resolution time (Contract 4). Do not set manually.
    p_exp_by_sequence: Dict[str, float] = Field(default_factory=dict)
    min_p_exp: Optional[float] = Field(default=None)
    computed_pool_size: Optional[int] = Field(default=None)


class ValueModelItem(BaseModel):
    testcd: str
    test: str
    unit: str
    plausible_min: float
    plausible_max: float
    baseline_mean: float
    baseline_sd: float
    trend_slope: float = 0.0
    trend_noise: float = 0.0


class VSModelDefaults(BaseModel):
    tests: List[ValueModelItem] = Field(default_factory=lambda: [
        ValueModelItem(testcd="SYSBP", test="Systolic Blood Pressure", unit="mmHg",
                      plausible_min=70, plausible_max=200, baseline_mean=120, baseline_sd=15),
        ValueModelItem(testcd="DIABP", test="Diastolic Blood Pressure", unit="mmHg",
                      plausible_min=40, plausible_max=130, baseline_mean=75, baseline_sd=10),
        ValueModelItem(testcd="PULSE", test="Pulse Rate", unit="beats/min",  # VSRESU C49673
                      plausible_min=40, plausible_max=150, baseline_mean=72, baseline_sd=12),
        ValueModelItem(testcd="TEMP", test="Temperature", unit="C",           # VSRESU C42559
                      plausible_min=35.0, plausible_max=42.0, baseline_mean=36.8, baseline_sd=0.4),
        ValueModelItem(testcd="RESP", test="Respiratory Rate", unit="breaths/min",  # VSRESU C49674
                      plausible_min=8, plausible_max=40, baseline_mean=16, baseline_sd=3),
        ValueModelItem(testcd="WEIGHT", test="Weight", unit="kg",
                      plausible_min=40, plausible_max=150, baseline_mean=70, baseline_sd=15),
        ValueModelItem(testcd="HEIGHT", test="Height", unit="cm",
                      plausible_min=140, plausible_max=210, baseline_mean=170, baseline_sd=10),
    ])


class LBModelDefaults(BaseModel):
    tests: List[ValueModelItem] = Field(default_factory=lambda: [
        ValueModelItem(testcd="ALT", test="Alanine Aminotransferase", unit="U/L",
                      plausible_min=5, plausible_max=500, baseline_mean=25, baseline_sd=10),
        ValueModelItem(testcd="AST", test="Aspartate Aminotransferase", unit="U/L",
                      plausible_min=5, plausible_max=500, baseline_mean=22, baseline_sd=8),
        ValueModelItem(testcd="CREAT", test="Creatinine", unit="umol/L",
                      plausible_min=30, plausible_max=500, baseline_mean=85, baseline_sd=20),
        ValueModelItem(testcd="GLUC", test="Glucose", unit="mmol/L",
                      plausible_min=2, plausible_max=30, baseline_mean=5.5, baseline_sd=1.2),
        ValueModelItem(testcd="HGB", test="Hemoglobin", unit="g/L",
                      plausible_min=70, plausible_max=200, baseline_mean=140, baseline_sd=15),
        ValueModelItem(testcd="WBC", test="Leukocytes", unit="10^9/L",
                      plausible_min=2, plausible_max=30, baseline_mean=7, baseline_sd=2),
        ValueModelItem(testcd="PLAT", test="Platelets", unit="10^9/L",
                      plausible_min=50, plausible_max=600, baseline_mean=250, baseline_sd=60),
    ])


class MedicalHistoryCondition(BaseModel):
    mhterm: str
    mhcat: str = "GENERAL"
    prevalence: float = Field(default=0.1, ge=0, le=1)
    typical_duration_years: Optional[float] = None
    can_be_ongoing: bool = True


class MedicalHistoryModelDefaults(BaseModel):
    generate_mh: bool = True
    capture_window_years: int = 10
    allow_ongoing_conditions: bool = True
    n_conditions_min: int = 0
    n_conditions_max: int = 5
    condition_library: List[MedicalHistoryCondition] = Field(default_factory=lambda: [
        MedicalHistoryCondition(mhterm="HYPERTENSION", mhcat="CARDIOVASCULAR", prevalence=0.3),
        MedicalHistoryCondition(mhterm="DIABETES MELLITUS TYPE 2", mhcat="ENDOCRINE", prevalence=0.15),
        MedicalHistoryCondition(mhterm="HYPERLIPIDEMIA", mhcat="METABOLIC", prevalence=0.25),
        MedicalHistoryCondition(mhterm="ASTHMA", mhcat="RESPIRATORY", prevalence=0.08),
        MedicalHistoryCondition(mhterm="DEPRESSION", mhcat="PSYCHIATRIC", prevalence=0.1),
        MedicalHistoryCondition(mhterm="GASTROESOPHAGEAL REFLUX DISEASE", mhcat="GASTROINTESTINAL", prevalence=0.15),
    ])


# Note: AEModelDefaults is defined earlier in this file (line ~121)


class CMModelDefaults(BaseModel):
    cm_rate_per_subject: float = 3.0
    cm_rate_sd: float = 2.0
    cm_library: List[Dict[str, str]] = Field(default_factory=lambda: [
        {"cmtrt": "PARACETAMOL", "cmroute": "ORAL", "cmdosfrq": "PRN"},
        {"cmtrt": "IBUPROFEN", "cmroute": "ORAL", "cmdosfrq": "PRN"},
        {"cmtrt": "OMEPRAZOLE", "cmroute": "ORAL", "cmdosfrq": "QD"},
        {"cmtrt": "METFORMIN", "cmroute": "ORAL", "cmdosfrq": "BID"},
        {"cmtrt": "ASPIRIN", "cmroute": "ORAL", "cmdosfrq": "QD"},
    ])


class ControlledTerminologyDefaults(BaseModel):
    aesev: List[str] = Field(default_factory=lambda: ["MILD", "MODERATE", "SEVERE"])
    aeser: List[str] = Field(default_factory=lambda: ["Y", "N"])
    aerel: List[str] = Field(default_factory=lambda: [
        "NOT RELATED", "UNLIKELY RELATED", "POSSIBLY RELATED", "PROBABLY RELATED", "DEFINITELY RELATED"
    ])
    aeout: List[str] = Field(default_factory=lambda: [
        "RECOVERED/RESOLVED", "RECOVERING/RESOLVING", "NOT RECOVERED/NOT RESOLVED",
        "RECOVERED/RESOLVED WITH SEQUELAE", "FATAL", "UNKNOWN"
    ])
    sex: List[str] = Field(default_factory=lambda: ["M", "F"])
    race: List[str] = Field(default_factory=lambda: [
        "WHITE", "BLACK OR AFRICAN AMERICAN", "ASIAN", "OTHER", "UNKNOWN"
    ])
    ethnic: List[str] = Field(default_factory=lambda: [
        "HISPANIC OR LATINO", "NOT HISPANIC OR LATINO", "UNKNOWN"
    ])


class TimeConventions(BaseModel):
    dtc_format: str = "datetime"
    timezone: str = "UTC"
    study_start_date_default: date = Field(default_factory=lambda: date(2024, 1, 15))
    study_start_date_jitter_days: int = Field(default=90, ge=0)


class DemographicsDefaults(BaseModel):
    age_min: int = 18
    age_max: int = 75
    age_mean: float = 45
    age_sd: float = 15
    sex_ratio_male: float = 0.5
    sex_distribution: Dict[str, float] = Field(default_factory=lambda: {
        "M": 0.5, "F": 0.5
    })
    race_distribution: Dict[str, float] = Field(default_factory=lambda: {
        "WHITE": 0.65, "BLACK OR AFRICAN AMERICAN": 0.15, "ASIAN": 0.10, "OTHER": 0.10
    })
    ethnic_distribution: Dict[str, float] = Field(default_factory=lambda: {
        "NOT HISPANIC OR LATINO": 0.85, "HISPANIC OR LATINO": 0.12, "UNKNOWN": 0.03
    })
    country: str = "USA"
    sites: List[str] = Field(default_factory=lambda: ["SITE001", "SITE002", "SITE003"])
    n_sites: int = 3
    total_subjects: int = 100
    subjects_per_arm: Dict[str, int] = Field(default_factory=dict)


class TSParameter(BaseModel):
    tsparmcd: str
    tsval: str


class Assumption(BaseModel):
    parameter: str
    assumed_value: Any
    reason: str
    source: str = "default"
    overridable: bool = True


class TrialDesignSpec(BaseModel):
    """Complete Trial Design Specification."""
    study_id: str
    title: str = ""
    phase: str = "2"
    therapeutic_area: str = ""
    n_subjects_default: int = Field(default=30, ge=1)
    arms: List[ArmSpec] = Field(default_factory=list)
    elements: List[ElementSpec] = Field(default_factory=list)
    arm_paths: List[ArmPath] = Field(default_factory=list)
    visits: List[VisitSpec] = Field(default_factory=list)
    ts_parameters: List[TSParameter] = Field(default_factory=list)
    disposition_model: DispositionModelDefaults = Field(default_factory=DispositionModelDefaults)
    vs_model: VSModelDefaults = Field(default_factory=VSModelDefaults)
    lb_model: LBModelDefaults = Field(default_factory=LBModelDefaults)
    mh_model: MedicalHistoryModelDefaults = Field(default_factory=MedicalHistoryModelDefaults)
    ae_model: AEModelDefaults = Field(default_factory=AEModelDefaults)
    cm_model: CMModelDefaults = Field(default_factory=CMModelDefaults)
    controlled_terminology: ControlledTerminologyDefaults = Field(default_factory=ControlledTerminologyDefaults)
    time_conventions: TimeConventions = Field(default_factory=TimeConventions)
    demographics: DemographicsDefaults = Field(default_factory=DemographicsDefaults)
    assumptions: List[Assumption] = Field(default_factory=list)
    
    # v2: Explicit arm order for deterministic iteration (§2.2)
    arm_order: List[str] = Field(default_factory=list)
    
    # v2: Protocol-planned total study days (Contract 6)
    total_study_days: int = Field(default=0, ge=0)
    
    # v2: Crossover sequence definitions (§2.5)
    crossover_sequences: List[Dict[str, Any]] = Field(default_factory=list)
    
    # v2: Is this a crossover design?
    is_crossover: bool = Field(default=False)
    
    # v2: Low shaped exposure probability override
    allow_low_shaped_exposure_probability: bool = Field(default=False)
    
    # v2: Study seed for reproducibility
    study_seed: int = Field(default=42)
    
    # Aliases for backward compatibility
    @property
    def demographics_defaults(self) -> DemographicsDefaults:
        return self.demographics
    
    @property
    def disposition_model_defaults(self) -> DispositionModelDefaults:
        return self.disposition_model
    
    def get_arm_order_list(self) -> List[str]:
        """Get explicit arm order or derive from arms list."""
        if self.arm_order:
            return self.arm_order
        return [arm.armcd for arm in self.arms]
    
    def compute_total_study_days(self) -> int:
        """Compute total study days from elements if not set."""
        if self.total_study_days > 0:
            return self.total_study_days
        total = sum(elem.nominal_duration_days or 0 for elem in self.elements)
        return total if total > 0 else 200
    
    def get_epochs(self) -> List[str]:
        seen = set()
        epochs = []
        for elem in self.elements:
            if elem.epoch not in seen:
                epochs.append(elem.epoch)
                seen.add(elem.epoch)
        return epochs
    
    def get_arm_codes(self) -> List[str]:
        return [arm.armcd for arm in self.arms]
    
    def get_element_by_etcd(self, etcd: str) -> Optional[ElementSpec]:
        for elem in self.elements:
            if elem.etcd == etcd:
                return elem
        return None
    
    # Alias for backward compatibility
    def get_element_by_code(self, etcd: str) -> Optional[ElementSpec]:
        return self.get_element_by_etcd(etcd)
    
    def get_arm_by_armcd(self, armcd: str) -> Optional[ArmSpec]:
        for arm in self.arms:
            if arm.armcd == armcd:
                return arm
        return None
    
    # Alias for backward compatibility
    def get_arm_by_code(self, armcd: str) -> Optional[ArmSpec]:
        return self.get_arm_by_armcd(armcd)
    
    def get_arm_path(self, armcd: str) -> Optional[ArmPath]:
        for path in self.arm_paths:
            if path.armcd == armcd:
                return path
        return None
    
    def get_element_sequence_for_arm(self, armcd: str) -> List[str]:
        """Get ordered list of element codes for an arm."""
        arm_path = self.get_arm_path(armcd)
        if arm_path is None:
            return []
        items = sorted(arm_path.elements, key=lambda x: x.taetord)
        return [item.etcd for item in items]


class ProtocolDraftSpec(BaseModel):
    extracted_spec: Dict[str, Any] = Field(default_factory=dict)
    assumptions_needed: List[str] = Field(default_factory=list)
    extraction_notes: List[str] = Field(default_factory=list)
    source_protocol: str = ""
