"""
SDTM Synthetic Data Generator - Subject Backbone Generator

This module generates the Demographics (DM) dataset and maintains 
a SubjectRegistry for consistent subject information across all domains.
"""

from __future__ import annotations
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field
from datetime import date, timedelta
import pandas as pd

from ..spec.models import TrialDesignSpec, DemographicsDefaults
from ..utils.rng import SyntheticRNG, get_rng
from ..utils.ids import SubjectIDGenerator, InvestigatorNameGenerator
from ..utils.dates import format_iso_date, add_days


@dataclass
class SubjectInfo:
    """Information about a single subject."""
    usubjid: str
    subjid: str
    siteid: str
    armcd: str
    arm: str
    age: int
    ageu: str
    sex: str
    race: str
    ethnic: str
    country: str
    rfstdtc: Optional[str]  # Reference start date (first dose)
    rfendtc: Optional[str]  # Reference end date
    rfxstdtc: Optional[str]  # First exposure date
    rfxendtc: Optional[str]  # Last exposure date
    rficdtc: Optional[str]  # Informed consent date
    rfpendtc: Optional[str]  # Last participation date
    brthdtc: Optional[str] = None  # Birth date (SDTM Expected)
    dthdtc: Optional[str] = None   # Death date (SDTM Expected)
    dthfl: Optional[str] = None    # Death flag Y/N (SDTM Expected)
    invnam: str = ""  # Investigator name
    screen_failure: bool = False
    completed: bool = True
    dropout_epoch: Optional[str] = None
    dropout_reason: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for DataFrame.
        
        SD1363/SD2237 FIX: Screen failures should have ARM/ARMCD/ACTARM/ACTARMCD 
        all null, with reason documented in ARMNRS.
        
        SD1366 FIX: Screen failures should NOT have RFSTDTC/RFENDTC populated.
        When ARMNRS is populated, these dates must be blank.
        """
        # SD1363/SD2237/SD1366: Screen failures get different treatment
        if self.screen_failure:
            armcd = ''
            arm = ''
            actarmcd = ''
            actarm = ''
            armnrs = 'SCREEN FAILURE'
            # SD1366: Screen failures should NOT have RFSTDTC/RFENDTC
            rfstdtc = ''
            rfendtc = ''
            rfxstdtc = ''
            rfxendtc = ''
        else:
            armcd = self.armcd
            arm = self.arm
            actarmcd = self.armcd
            actarm = self.arm
            armnrs = ''
            rfstdtc = self.rfstdtc if self.rfstdtc else ''
            rfendtc = self.rfendtc if self.rfendtc else ''
            rfxstdtc = self.rfxstdtc if self.rfxstdtc else ''
            rfxendtc = self.rfxendtc if self.rfxendtc else ''
        
        return {
            'USUBJID': self.usubjid,
            'SUBJID': self.subjid,
            'SITEID': self.siteid,
            'ARMCD': armcd,
            'ARM': arm,
            'ACTARMCD': actarmcd,
            'ACTARM': actarm,
            'ARMNRS': armnrs,
            'ACTARMUD': '',  # Unplanned treatment description - populated by conformance layer
            'AGE': self.age,
            'AGEU': self.ageu,
            'SEX': self.sex,
            'RACE': self.race,
            'ETHNIC': self.ethnic,
            'COUNTRY': self.country,
            'BRTHDTC': self.brthdtc or '',
            'RFSTDTC': rfstdtc,
            'RFENDTC': rfendtc,
            'RFXSTDTC': rfxstdtc,
            'RFXENDTC': rfxendtc,
            'RFICDTC': self.rficdtc,
            'RFPENDTC': self.rfpendtc if self.rfpendtc else '',
            'DTHDTC': self.dthdtc or '',
            'DTHFL': self.dthfl or '',
            'INVNAM': self.invnam,
        }


class SubjectRegistry:
    """
    Registry of all subjects in the study.
    
    Provides centralized access to subject information for all generators.
    """
    
    def __init__(self):
        """Initialize the registry."""
        self._subjects: Dict[str, SubjectInfo] = {}
        self._by_arm: Dict[str, List[str]] = {}
        self._by_site: Dict[str, List[str]] = {}
    
    def add_subject(self, subject: SubjectInfo) -> None:
        """Add a subject to the registry."""
        self._subjects[subject.usubjid] = subject
        
        if subject.armcd not in self._by_arm:
            self._by_arm[subject.armcd] = []
        self._by_arm[subject.armcd].append(subject.usubjid)
        
        if subject.siteid not in self._by_site:
            self._by_site[subject.siteid] = []
        self._by_site[subject.siteid].append(subject.usubjid)
    
    def get_subject(self, usubjid: str) -> Optional[SubjectInfo]:
        """Get subject by USUBJID."""
        return self._subjects.get(usubjid)
    
    def get_all_subjects(self) -> List[SubjectInfo]:
        """Get all subjects."""
        return list(self._subjects.values())
    
    def get_subjects_by_arm(self, armcd: str) -> List[SubjectInfo]:
        """Get all subjects in an arm."""
        usubjids = self._by_arm.get(armcd, [])
        return [self._subjects[uid] for uid in usubjids]
    
    def get_subjects_by_site(self, siteid: str) -> List[SubjectInfo]:
        """Get all subjects at a site."""
        usubjids = self._by_site.get(siteid, [])
        return [self._subjects[uid] for uid in usubjids]
    
    def get_enrolled_subjects(self) -> List[SubjectInfo]:
        """Get all subjects who passed screening (not screen failures)."""
        return [s for s in self._subjects.values() if not s.screen_failure]
    
    def get_screen_failures(self) -> List[SubjectInfo]:
        """Get all screen failure subjects."""
        return [s for s in self._subjects.values() if s.screen_failure]
    
    def get_completers(self) -> List[SubjectInfo]:
        """Get all subjects who completed the study."""
        return [s for s in self._subjects.values() 
                if not s.screen_failure and s.completed]
    
    def get_dropouts(self) -> List[SubjectInfo]:
        """Get all subjects who dropped out."""
        return [s for s in self._subjects.values() 
                if not s.screen_failure and not s.completed]
    
    @property
    def n_subjects(self) -> int:
        """Total number of subjects."""
        return len(self._subjects)
    
    @property
    def n_enrolled(self) -> int:
        """Number of enrolled (non-screen-failure) subjects."""
        return len(self.get_enrolled_subjects())


class SubjectBackboneGenerator:
    """
    Generates the Demographics (DM) dataset and populates the SubjectRegistry.
    
    Handles:
    - Subject ID generation
    - Demographics generation (age, sex, race, etc.)
    - Arm assignment
    - Screen failure and dropout simulation
    - Reference dates (consent, first dose, last dose)
    """
    
    def __init__(self, spec: TrialDesignSpec, seed: Optional[int] = None):
        """
        Initialize the generator.
        
        Args:
            spec: Trial design specification
            seed: Random seed (uses global RNG if None)
        """
        self.spec = spec
        self.rng = get_rng(seed) if seed else get_rng()
        self.registry = SubjectRegistry()
        self.id_generator = SubjectIDGenerator(
            study_id=spec.study_id,
            n_sites=spec.demographics_defaults.n_sites
        )
        self.inv_name_gen = InvestigatorNameGenerator()
    
    def generate(self, n_subjects: Optional[int] = None) -> tuple:
        """
        Generate DM dataset and populate registry.
        
        Args:
            n_subjects: Number of subjects (uses spec default if None)
            
        Returns:
            Tuple of (DM DataFrame, SubjectRegistry)
        """
        n = n_subjects or self.spec.n_subjects_default
        defaults = self.spec.demographics_defaults
        disp = self.spec.disposition_model_defaults
        
        # Calculate subjects per arm - use spec if defined, otherwise equal
        n_arms = len(self.spec.arms)
        
        # Check if specific allocation is defined in spec
        spec_allocation = defaults.subjects_per_arm
        if spec_allocation and sum(spec_allocation.values()) > 0:
            # Use specified allocation, scaled to target n
            total_specified = sum(spec_allocation.values())
            subjects_per_arm = {}
            allocated = 0
            arm_list = list(self.spec.arms)
            
            for i, arm in enumerate(arm_list):
                if arm.armcd in spec_allocation:
                    ratio = spec_allocation[arm.armcd] / total_specified
                    if i == len(arm_list) - 1:
                        # Last arm gets remainder to ensure exact total
                        subjects_per_arm[arm.armcd] = n - allocated
                    else:
                        arm_n = int(round(n * ratio))
                        subjects_per_arm[arm.armcd] = arm_n
                        allocated += arm_n
                else:
                    # Arm not in allocation, give equal share of remaining
                    subjects_per_arm[arm.armcd] = n // n_arms
        else:
            # Equal allocation (default behavior)
            base_per_arm = n // n_arms
            remainder = n % n_arms
            
            subjects_per_arm = {
                arm.armcd: base_per_arm + (1 if i < remainder else 0)
                for i, arm in enumerate(self.spec.arms)
            }
        
        # Generate subjects
        subjects = []
        subject_idx = 0
        
        for arm in self.spec.arms:
            n_in_arm = subjects_per_arm[arm.armcd]
            
            for _ in range(n_in_arm):
                # Assign to site
                site_idx = subject_idx % defaults.n_sites
                
                # Generate IDs
                usubjid = self.id_generator.generate_usubjid(site_idx)
                subjid = self.id_generator.get_subjid_from_usubjid(usubjid)
                siteid = self.id_generator.get_siteid_from_usubjid(usubjid)
                
                # Generate demographics
                age = self._generate_age(defaults)
                sex = self._generate_categorical(defaults.sex_distribution)
                race = self._generate_categorical(defaults.race_distribution)
                ethnic = self._generate_categorical(defaults.ethnic_distribution)
                
                # Determine disposition
                is_screen_failure = self.rng.bernoulli(disp.screen_fail_rate)
                
                if is_screen_failure:
                    completed = False
                    dropout_epoch = "SCREENING"
                    dropout_reason = "SCREEN FAILURE"
                else:
                    # Check for dropout by epoch
                    completed = True
                    dropout_epoch = None
                    dropout_reason = None
                    
                    for epoch, rate in disp.dropout_rate_by_epoch.items():
                        if self.rng.bernoulli(rate):
                            completed = False
                            dropout_epoch = epoch
                            dropout_reason = self.rng.choice(
                                [c for c in disp.ds_categories if c != "COMPLETED"]
                            )
                            break
                    
                    # If no epoch-specific dropout, check overall completion
                    if completed and not self.rng.bernoulli(disp.completion_rate):
                        completed = False
                        dropout_reason = self.rng.choice(
                            [c for c in disp.ds_categories if c != "COMPLETED"]
                        )
                
                # Generate dates
                study_start = self.spec.time_conventions.study_start_date_default
                jitter = self.spec.time_conventions.study_start_date_jitter_days
                
                # Informed consent date (enrollment window)
                consent_offset = self.rng.randint(0, jitter)
                consent_date = add_days(study_start, consent_offset)
                rficdtc = format_iso_date(consent_date)
                
                if is_screen_failure:
                    # Screen failures have no first dose, but must have RFENDTC
                    # SD1031 FIX: Screen failures get RFENDTC = RFPENDTC
                    screen_fail_date = add_days(consent_date, self.rng.randint(1, 28))
                    rfstdtc = None
                    rfendtc = format_iso_date(screen_fail_date)  # SD1031: always populate
                    rfxstdtc = None
                    rfxendtc = None
                    rfpendtc = format_iso_date(screen_fail_date)
                else:
                    # Calculate first dose date (after screening)
                    screening_duration = self.rng.randint(7, 35)
                    first_dose_date = add_days(consent_date, screening_duration)
                    rfstdtc = format_iso_date(first_dose_date)
                    rfxstdtc = rfstdtc
                    
                    # Get planned durations from arm path
                    treatment_duration = self._get_treatment_duration(arm.armcd)
                    follow_up_duration = self._get_followup_duration()
                    
                    # Calculate planned end dates
                    planned_treatment_end = add_days(first_dose_date, treatment_duration - 1)
                    planned_study_end = add_days(planned_treatment_end, follow_up_duration)
                    
                    if completed:
                        # Full treatment and follow-up
                        last_dose_date = planned_treatment_end
                        end_date = planned_study_end
                    else:
                        # Early termination - determine when and where
                        total_duration = treatment_duration + follow_up_duration
                        dropout_day = self.rng.randint(1, total_duration)
                        dropout_date = add_days(first_dose_date, dropout_day - 1)
                        
                        # Determine if dropout is during treatment or follow-up
                        if dropout_day <= treatment_duration:
                            # Dropout during treatment
                            dropout_epoch = dropout_epoch or 'TREATMENT'
                            last_dose_date = dropout_date
                            end_date = dropout_date
                        else:
                            # Dropout during follow-up (treatment completed, follow-up incomplete)
                            dropout_epoch = dropout_epoch or 'FOLLOW-UP'
                            last_dose_date = planned_treatment_end  # Treatment was completed
                            end_date = dropout_date  # Participation ended during follow-up
                    
                    rfendtc = format_iso_date(end_date)
                    rfxendtc = format_iso_date(last_dose_date)
                    rfpendtc = rfendtc
                
                # Calculate birth date from age and informed consent date
                # Birth year = consent year - age (approximate)
                brthdtc = None
                if rficdtc and age:
                    from datetime import datetime
                    consent_date = datetime.strptime(rficdtc, "%Y-%m-%d").date()
                    birth_year = consent_date.year - age
                    # Use January 1 of birth year (partial date per SDTM)
                    brthdtc = f"{birth_year}"  # Year-only partial date
                
                # Create subject
                subject = SubjectInfo(
                    usubjid=usubjid,
                    subjid=subjid,
                    siteid=siteid,
                    armcd=arm.armcd,
                    arm=arm.arm,
                    age=age,
                    ageu="YEARS",
                    sex=sex,
                    race=race,
                    ethnic=ethnic,
                    country=defaults.country,
                    rfstdtc=rfstdtc,
                    rfendtc=rfendtc,
                    rfxstdtc=rfxstdtc,
                    rfxendtc=rfxendtc,
                    rficdtc=rficdtc,
                    rfpendtc=rfpendtc,
                    brthdtc=brthdtc,
                    invnam=self.inv_name_gen.get_investigator_name(siteid, self.rng),
                    screen_failure=is_screen_failure,
                    completed=completed,
                    dropout_epoch=dropout_epoch,
                    dropout_reason=dropout_reason,
                )
                
                subjects.append(subject)
                self.registry.add_subject(subject)
                subject_idx += 1
        
        # Create DataFrame
        records = [s.to_dict() for s in subjects]
        df = pd.DataFrame(records)
        
        # Add domain column
        df.insert(0, 'STUDYID', self.spec.study_id)
        df.insert(1, 'DOMAIN', 'DM')
        
        # Ensure column order per SDTM-IG v3.4
        # Note: ACTARMUD removed (SD1149) - only include if actually used
        cols = [
            'STUDYID', 'DOMAIN', 'USUBJID', 'SUBJID', 'SITEID',
            'BRTHDTC', 'AGE', 'AGEU', 'SEX', 'RACE', 'ETHNIC',
            'ARMCD', 'ARM', 'ACTARMCD', 'ACTARM', 'ARMNRS',
            'COUNTRY', 'INVNAM',
            'RFSTDTC', 'RFENDTC', 'RFXSTDTC', 'RFXENDTC',
            'RFICDTC', 'RFPENDTC', 'DTHDTC', 'DTHFL'
        ]
        
        # Sort by USUBJID for deterministic output
        df = df.sort_values('USUBJID').reset_index(drop=True)
        
        return df[[c for c in cols if c in df.columns]], self.registry
    
    def _generate_age(self, defaults: DemographicsDefaults) -> int:
        """Generate age from truncated normal distribution."""
        return int(self.rng.truncated_normal(
            mean=defaults.age_mean,
            std=defaults.age_sd,
            low=defaults.age_min,
            high=defaults.age_max
        ))
    
    def _generate_categorical(self, distribution: Dict[str, float]) -> str:
        """Generate value from categorical distribution."""
        return self.rng.sample_from_distribution(distribution, n=1)[0]
    
    def _get_treatment_duration(self, armcd: str) -> int:
        """Get treatment duration in days for an arm."""
        # Find the treatment element duration
        element_sequence = self.spec.get_element_sequence_for_arm(armcd)
        if not element_sequence:
            return 84  # Default 12 weeks
        
        total = 0
        for etcd in element_sequence:
            elem = self.spec.get_element_by_etcd(etcd)
            if elem and elem.epoch.upper().startswith("TREATMENT"):
                if elem.nominal_duration_days:
                    total += elem.nominal_duration_days
        
        return total if total > 0 else 84
    
    def _get_followup_duration(self) -> int:
        """Get follow-up duration in days."""
        for elem in self.spec.elements:
            if elem.epoch.upper() == "FOLLOW-UP":
                return elem.nominal_duration_days or 28
        return 28
    
    def _get_total_study_duration(self) -> int:
        """Get total study duration in days."""
        total = sum(
            elem.nominal_duration_days or 0 
            for elem in self.spec.elements
        )
        return total if total > 0 else 200
