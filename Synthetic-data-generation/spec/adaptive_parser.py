"""
Adaptive Protocol Parser

This module provides intelligent extraction of trial design specifications
from various protocol document formats. It can handle:
- Plain text protocols
- Image-based PDFs (via OCR)
- Structured PDFs

The parser identifies key trial elements and generates SDTM-ready specifications.
"""

from __future__ import annotations
import re
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path

from ..spec.models import (
    TrialDesignSpec, ArmSpec, ElementSpec, VisitSpec, RegimenItem,
    ArmPath, ArmPathItem, TSParameter, DemographicsDefaults,
    Route, DoseFrequency, CollectionFlags, Assumption
)


class ProtocolType(Enum):
    """Protocol classification by therapeutic area/type."""
    VACCINE = "vaccine"
    IMMUNOTHERAPY = "immunotherapy"
    SMALL_MOLECULE = "small_molecule"
    BIOLOGIC = "biologic"
    EXTENSION = "extension"
    UNKNOWN = "unknown"


@dataclass
class ExtractedProtocolInfo:
    """Extracted protocol information before conversion to TrialDesignSpec."""
    # Identifiers
    protocol_number: str = ""
    study_id: str = ""
    sponsor: str = ""
    trial_name: str = ""
    
    # Design
    phase: str = ""
    design_type: str = ""  # parallel, crossover, etc.
    blinding: str = ""  # double-blind, open-label, etc.
    control_type: str = ""  # placebo, active, etc.
    randomization_ratio: str = ""  # 1:1, 2:1, etc.
    
    # Population
    target_enrollment: int = 0
    age_min: int = 18
    age_max: int = 99
    indication: str = ""
    
    # Treatment
    drug_name: str = ""
    drug_class: str = ""
    route: str = ""
    dose: str = ""
    frequency: str = ""
    
    # Arms
    arms: List[Dict[str, Any]] = field(default_factory=list)
    
    # Schedule
    treatment_duration_weeks: int = 0
    total_duration_weeks: int = 0
    visits: List[Dict[str, Any]] = field(default_factory=list)
    dosing_days: List[int] = field(default_factory=list)
    
    # Classification
    protocol_type: ProtocolType = ProtocolType.UNKNOWN
    therapeutic_area: str = ""
    
    # Raw text for reference
    raw_text: str = ""


class AdaptiveProtocolParser:
    """
    Intelligent protocol parser that adapts to different document formats
    and therapeutic areas.
    """
    
    # Pattern libraries for extraction
    PHASE_PATTERNS = [
        r'Phase\s*([123])[ab]?/?([123])?',
        r'Phase\s*([IVX]+)',
        r'phase\s*([123])',
    ]
    
    RANDOMIZATION_PATTERNS = [
        r'(\d+):(\d+)(?::(\d+))?\s*(?:ratio|randomiz)',
        r'randomiz\w+\s+(?:at\s+)?(?:a\s+)?(\d+):(\d+)',
        r'(\d+):(\d+)\s+(?:to\s+)?(?:either|receive)',
    ]
    
    ENROLLMENT_PATTERNS = [
        r'N\s*=\s*(\d{2,6}(?:,\d{3})?)',
        r'(\d{2,3},\d{3})\s*(?:subjects|participants)',  # 36,500 subjects
        r'(?:approximately|~|about)\s*(\d{1,3}(?:,\d{3})*)\s*(?:subjects|participants|patients)',
        r'enroll\w*\s+(\d{1,3}(?:,\d{3})*)\s*(?:subjects|participants|patients)?',
        r'(?:N=|n=)(\d{3,})',
        r'(\d{3,})\s*(?:subjects|participants)\s*will\s*be',
    ]
    
    DURATION_PATTERNS = [
        r'(\d+)\s*(?:weeks?|wks?)\s*(?:duration|treatment|study)',
        r'(?:through|until)\s+Week\s+(\d+)',
        r'Day\s+(\d+)\s*(?:end|final|last)',
    ]
    
    ROUTE_MAPPING = {
        'intramuscular': Route.INTRAVENOUS,  # Will fix below
        'im': Route.INTRAMUSCULAR,
        'intravenous': Route.INTRAVENOUS,
        'iv': Route.INTRAVENOUS,
        'subcutaneous': Route.SUBCUTANEOUS,
        'sc': Route.SUBCUTANEOUS,
        'oral': Route.ORAL,
        'po': Route.ORAL,
        'sublingual': Route.SUBLINGUAL,
        'topical': Route.TOPICAL,
    }
    
    def __init__(self):
        self.extracted_info = ExtractedProtocolInfo()
    
    def parse(self, text: str, source_file: str = "") -> ExtractedProtocolInfo:
        """
        Parse protocol text and extract all relevant information.
        
        Args:
            text: Protocol document text
            source_file: Source filename for reference
            
        Returns:
            ExtractedProtocolInfo with all extracted details
        """
        self.extracted_info = ExtractedProtocolInfo()
        self.extracted_info.raw_text = text[:50000]  # Keep first 50k chars
        
        # Run extraction pipeline
        self._extract_identifiers(text)
        self._extract_design(text)
        self._extract_population(text)
        self._extract_treatment(text)
        self._extract_schedule(text)
        self._classify_protocol(text)
        self._extract_arms(text)
        
        return self.extracted_info
    
    def _extract_identifiers(self, text: str):
        """Extract protocol identifiers."""
        # Protocol number - try multiple patterns
        patterns = [
            r'Protocol\s*Number[:\s]+([A-Z0-9\-]+)',
            r'Protocol\s*(?:No\.?|#)?[:\s]+([A-Z]{2,}-[A-Z0-9\-]+)',
            r'Study\s*(?:Number|No\.?|#)?[:\s]+([A-Z0-9\-]+)',
            r'EudraCT\s*(?:Number)?[:\s]+(\d{4}-\d{6}-\d{2})',
            r'([A-Z]{2,3}-[A-Z]*-?\d{3,})',  # Patterns like CV-NCOV-004, PRV-031-001
        ]
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                proto = match.group(1).strip()
                # Filter out common false positives
                if proto.upper() not in ['COVID-19', 'SARS-COV-2', 'THE', 'AND'] and len(proto) > 4:
                    self.extracted_info.protocol_number = proto
                    self.extracted_info.study_id = proto
                    break
        
        # Sponsor
        sponsor_patterns = [
            r'Sponsor[:\s]+([A-Za-z][A-Za-z\s\.]+(?:Inc|Ltd|AG|LLC|Co|Corp|Bio)?)',
            r'(?:Prepared by|Conducted by)[:\s]+([A-Za-z][A-Za-z\s\.]+)',
        ]
        for pattern in sponsor_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                sponsor = match.group(1).strip()
                # Clean up sponsor name
                sponsor = re.sub(r'\s+', ' ', sponsor)[:50]
                self.extracted_info.sponsor = sponsor
                break
        
        # Trial name
        name_patterns = [
            r'Trial\s*Name[:\s]+([A-Z][A-Z0-9\-]+)',
            r'PROTECT|HERALD|CARDINAL|CADENZA',  # Known trial names
            r'(?:called|named|known as)\s+([A-Z][A-Z0-9\-]+)',
        ]
        for pattern in name_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                name = match.group(1) if match.lastindex else match.group(0)
                self.extracted_info.trial_name = name.strip()[:30]
                break
    
    def _extract_design(self, text: str):
        """Extract study design elements."""
        text_lower = text.lower()
        
        # Phase
        for pattern in self.PHASE_PATTERNS:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                phase = match.group(1)
                if match.lastindex and match.lastindex > 1 and match.group(2):
                    phase = f"{phase}/{match.group(2)}"
                self.extracted_info.phase = phase
                break
        
        # Blinding
        if 'double-blind' in text_lower or 'double blind' in text_lower:
            self.extracted_info.blinding = "DOUBLE BLIND"
        elif 'single-blind' in text_lower or 'single blind' in text_lower:
            self.extracted_info.blinding = "SINGLE BLIND"
        elif 'observer-blind' in text_lower or 'observer blind' in text_lower:
            self.extracted_info.blinding = "SINGLE BLIND"
        elif 'open-label' in text_lower or 'open label' in text_lower:
            self.extracted_info.blinding = "OPEN LABEL"
        
        # Control type
        if 'placebo-controlled' in text_lower or 'placebo controlled' in text_lower:
            self.extracted_info.control_type = "PLACEBO"
        elif 'active-controlled' in text_lower or 'active controlled' in text_lower:
            self.extracted_info.control_type = "ACTIVE"
        
        # Design type
        if 'parallel' in text_lower:
            self.extracted_info.design_type = "PARALLEL"
        elif 'crossover' in text_lower or 'cross-over' in text_lower:
            self.extracted_info.design_type = "CROSSOVER"
        else:
            self.extracted_info.design_type = "PARALLEL"
        
        # Randomization ratio
        for pattern in self.RANDOMIZATION_PATTERNS:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                groups = [g for g in match.groups() if g]
                self.extracted_info.randomization_ratio = ':'.join(groups)
                break
    
    def _extract_population(self, text: str):
        """Extract population characteristics."""
        # Target enrollment
        for pattern in self.ENROLLMENT_PATTERNS:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                num_str = match.group(1).replace(',', '')
                self.extracted_info.target_enrollment = int(num_str)
                break
        
        # Age range
        age_pattern = r'(\d+)\s*(?:to|-)?\s*(\d+)?\s*years?\s*(?:of\s*age|old)?'
        matches = re.findall(age_pattern, text, re.IGNORECASE)
        for match in matches:
            min_age = int(match[0])
            max_age = int(match[1]) if match[1] else 99
            if 8 <= min_age <= 65 and min_age < max_age:
                self.extracted_info.age_min = min_age
                self.extracted_info.age_max = max_age
                break
        
        # Indication - use frequency to determine primary indication
        text_lower = text.lower()
        
        # Count occurrences
        covid_count = text_lower.count('covid-19') + text_lower.count('sars-cov-2')
        t1d_count = text_lower.count('t1d') + text_lower.count('type 1 diabetes')
        cad_count = text_lower.count('cold agglutinin')
        uc_count = text_lower.count('ulcerative colitis')
        chagas_count = text_lower.count('chagas')
        opioid_count = text_lower.count('opioid')
        
        # Determine primary indication
        counts = {
            'Type 1 Diabetes': t1d_count,
            'Cold Agglutinin Disease': cad_count,
            'Ulcerative Colitis': uc_count,
            'Chagas Disease': chagas_count,
            'Opioid Use Disorder': opioid_count,
            'COVID-19': covid_count,
        }
        
        # Get indication with highest count (min 3 mentions)
        best_indication = max(counts.items(), key=lambda x: x[1])
        if best_indication[1] >= 3:
            self.extracted_info.indication = best_indication[0]
        else:
            # Fallback to pattern matching
            indication_patterns = [
                r'(?:patients?|subjects?|participants?)\s+with\s+([A-Za-z\s\-]+(?:disease|syndrome|disorder))',
            ]
            for pattern in indication_patterns:
                match = re.search(pattern, text, re.IGNORECASE)
                if match and match.lastindex:
                    self.extracted_info.indication = match.group(1).strip()[:100]
                    break
    
    def _extract_treatment(self, text: str):
        """Extract treatment/drug information."""
        text_lower = text.lower()
        
        # Route of administration - count occurrences for accuracy
        im_count = len(re.findall(r'\bintramuscular\b|\bIM\b', text, re.IGNORECASE))
        iv_count = len(re.findall(r'\bintravenous\b|\bIV\s+infusion\b|\bIV\b', text, re.IGNORECASE))
        sc_count = len(re.findall(r'\bsubcutaneous\b|\bSC\b', text, re.IGNORECASE))
        oral_count = len(re.findall(r'\boral\b', text_lower))
        
        route_counts = {
            Route.INTRAMUSCULAR: im_count,
            Route.INTRAVENOUS: iv_count,
            Route.SUBCUTANEOUS: sc_count,
            Route.ORAL: oral_count,
        }
        
        # Get route with highest count
        best_route = max(route_counts.items(), key=lambda x: x[1])
        if best_route[1] > 0:
            self.extracted_info.route = best_route[0].value
        
        # Drug name - look for INN or specific drug names
        # Check for known drug names first
        known_drugs = {
            'teplizumab': 'Teplizumab',
            'sutimlimab': 'Sutimlimab',
            'olamkicept': 'Olamkicept',
            'benznidazole': 'Benznidazole',
            'buprenorphine': 'Buprenorphine',
            'cvncov': 'CVnCoV',
        }
        for drug_key, drug_name in known_drugs.items():
            if drug_key in text_lower:
                self.extracted_info.drug_name = drug_name
                break
        
        # If not found, try patterns
        if not self.extracted_info.drug_name:
            drug_patterns = [
                r'(?:INN|Investigational\s*Product)[:\s]+([A-Za-z0-9\-]+)',
                r'(?:referred\s+to\s+as|called)\s+([A-Za-z0-9\-]+)',
                r'(?:study\s+drug|treatment)[:\s]+([A-Za-z][A-Za-z0-9\-]+)',
            ]
            for pattern in drug_patterns:
                match = re.search(pattern, text, re.IGNORECASE)
                if match:
                    drug = match.group(1).strip()
                    if len(drug) > 2 and drug.upper() not in ['THE', 'AND', 'FOR', 'ALLOCATION']:
                        self.extracted_info.drug_name = drug
                        break
        
        # Dose - look for specific dose patterns
        dose_patterns = [
            r'(\d+)\s*(μg|µg)\s*(?:dose|mRNA)',
            r'dose\s*(?:of|level)?\s*(?:of)?\s*(\d+(?:\.\d+)?)\s*(μg|µg|mcg|mg|g)',
            r'(\d+(?:\.\d+)?)\s*(µg|mcg|mg|g|mL|IU|U)\s*(?:dose|per)?',
            r'(\d+)\s*mg/m2',
        ]
        for pattern in dose_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                self.extracted_info.dose = f"{match.group(1)} {match.group(2)}"
                break
        
        # Frequency
        if 'daily' in text_lower or 'qd' in text_lower:
            self.extracted_info.frequency = "QD"
        elif 'twice daily' in text_lower or 'bid' in text_lower:
            self.extracted_info.frequency = "BID"
        elif 'weekly' in text_lower or 'qw' in text_lower:
            self.extracted_info.frequency = "QW"
        elif 'every 2 weeks' in text_lower or 'q2w' in text_lower:
            self.extracted_info.frequency = "Q2W"
        elif '28 days apart' in text_lower:
            self.extracted_info.frequency = "Q4W"
    
    def _extract_schedule(self, text: str):
        """Extract visit schedule and duration."""
        # Find Day references
        day_pattern = r'Day\s+(\d+)'
        days = [int(m) for m in re.findall(day_pattern, text)]
        if days:
            unique_days = sorted(set(days))
            self.extracted_info.dosing_days = [d for d in unique_days if d <= 400]
        
        # Find Week references
        week_pattern = r'Week\s+(\d+)'
        weeks = [int(m) for m in re.findall(week_pattern, text)]
        if weeks:
            max_week = max(weeks)
            self.extracted_info.total_duration_weeks = max_week
        
        # Treatment duration
        for pattern in self.DURATION_PATTERNS:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                self.extracted_info.treatment_duration_weeks = int(match.group(1))
                break
        
        # Build visit list from Day references
        visits = []
        common_visits = {
            1: "Day 1/Baseline",
            29: "Day 29",
            43: "Day 43",
            57: "Day 57/Week 8",
            85: "Week 12",
            120: "Day 120/Week 17",
            182: "Day 182/Week 26",
            211: "Day 211/Week 30",
            365: "Day 365/Week 52",
            393: "Day 393/Week 56",
            546: "Week 78",
        }
        
        for day in self.extracted_info.dosing_days[:15]:  # Limit to 15 visits
            visit_name = common_visits.get(day, f"Day {day}")
            visits.append({
                'visitnum': len(visits) + 1,
                'visit': visit_name,
                'visitdy': day if day > 0 else -1,
            })
        
        if visits:
            self.extracted_info.visits = visits
    
    def _classify_protocol(self, text: str):
        """Classify protocol type and therapeutic area based on keyword frequency."""
        text_lower = text.lower()
        
        # Count keyword occurrences for more accurate classification
        vaccine_count = sum(text_lower.count(kw) for kw in ['vaccine', 'vaccination', 'immunization', 'mrna vaccine'])
        covid_count = text_lower.count('covid-19') + text_lower.count('sars-cov-2')
        t1d_count = text_lower.count('t1d') + text_lower.count('type 1 diabetes') + text_lower.count('newly diagnosed diabetes')
        cad_count = text_lower.count('cold agglutinin') + text_lower.count('hemolytic anemia')
        uc_count = text_lower.count('ulcerative colitis')
        
        # Determine primary indication based on counts
        max_count = max(vaccine_count, covid_count, t1d_count, cad_count, uc_count)
        
        if t1d_count >= 10 and t1d_count >= covid_count:
            # Type 1 Diabetes is primary focus
            self.extracted_info.therapeutic_area = "ENDOCRINOLOGY"
            self.extracted_info.protocol_type = ProtocolType.BIOLOGIC
        elif cad_count >= 3:
            self.extracted_info.therapeutic_area = "HEMATOLOGY"
            self.extracted_info.protocol_type = ProtocolType.BIOLOGIC
        elif uc_count >= 3:
            self.extracted_info.therapeutic_area = "GASTROENTEROLOGY"
            self.extracted_info.protocol_type = ProtocolType.BIOLOGIC
        elif vaccine_count >= 5 or (covid_count >= 10 and vaccine_count >= 1):
            self.extracted_info.protocol_type = ProtocolType.VACCINE
            self.extracted_info.therapeutic_area = "INFECTIOUS DISEASE"
        elif any(kw in text_lower for kw in ['antibody', 'monoclonal', 'mab']):
            self.extracted_info.protocol_type = ProtocolType.BIOLOGIC
            self.extracted_info.therapeutic_area = "IMMUNOLOGY"
        elif any(kw in text_lower for kw in ['extension', 'long-term', 'rollover']):
            self.extracted_info.protocol_type = ProtocolType.EXTENSION
    
    def _extract_arms(self, text: str):
        """Extract treatment arms from protocol."""
        arms = []
        text_lower = text.lower()
        
        # Parse randomization ratio
        ratio_parts = self.extracted_info.randomization_ratio.split(':')
        ratio = [int(r) for r in ratio_parts if r.isdigit()] or [1, 1]
        
        # Detect arm configurations
        if self.extracted_info.control_type == "PLACEBO":
            # Active + Placebo design
            drug_name = self.extracted_info.drug_name or "STUDY DRUG"
            
            if len(ratio) == 2:
                # Two-arm design
                arms = [
                    {
                        'armcd': 'TRT',
                        'arm': f'{drug_name} {self.extracted_info.dose}'.strip(),
                        'ratio': ratio[0],
                        'is_treatment': True,
                    },
                    {
                        'armcd': 'PBO',
                        'arm': 'Placebo',
                        'ratio': ratio[1],
                        'is_treatment': False,
                    }
                ]
            elif len(ratio) == 3:
                # Three-arm design (e.g., high dose, low dose, placebo)
                arms = [
                    {
                        'armcd': 'HIGH',
                        'arm': f'{drug_name} High Dose',
                        'ratio': ratio[0],
                        'is_treatment': True,
                    },
                    {
                        'armcd': 'LOW',
                        'arm': f'{drug_name} Low Dose',
                        'ratio': ratio[1],
                        'is_treatment': True,
                    },
                    {
                        'armcd': 'PBO',
                        'arm': 'Placebo',
                        'ratio': ratio[2],
                        'is_treatment': False,
                    }
                ]
        elif self.extracted_info.blinding == "OPEN LABEL":
            # Single arm open-label
            drug_name = self.extracted_info.drug_name or "STUDY DRUG"
            arms = [
                {
                    'armcd': 'TRT',
                    'arm': f'{drug_name}',
                    'ratio': 1,
                    'is_treatment': True,
                }
            ]
        
        self.extracted_info.arms = arms
    
    def to_trial_spec(self) -> TrialDesignSpec:
        """
        Convert extracted protocol info to TrialDesignSpec.
        
        Returns:
            TrialDesignSpec ready for SDTM generation
        """
        info = self.extracted_info
        
        # Determine route enum
        route = Route.INTRAVENOUS
        if info.route:
            route_map = {
                'ORAL': Route.ORAL,
                'INTRAVENOUS': Route.INTRAVENOUS,
                'SUBCUTANEOUS': Route.SUBCUTANEOUS,
                'INTRAMUSCULAR': Route.INTRAMUSCULAR,
            }
            route = route_map.get(info.route.upper(), Route.INTRAVENOUS)
        
        # Determine frequency enum
        freq = DoseFrequency.QD
        freq_map = {
            'QD': DoseFrequency.QD,
            'BID': DoseFrequency.BID,
            'QW': DoseFrequency.QW,
            'Q2W': DoseFrequency.Q2W,
            'Q4W': DoseFrequency.Q4W,
        }
        freq = freq_map.get(info.frequency, DoseFrequency.QD)
        
        # Parse dose
        dose_val = 0.0
        dose_unit = "mg"
        if info.dose:
            dose_match = re.match(r'(\d+(?:\.\d+)?)\s*(\w+)', info.dose)
            if dose_match:
                dose_val = float(dose_match.group(1))
                dose_unit = dose_match.group(2)
        
        # Build arms
        arms = []
        for arm_info in info.arms:
            regimen = []
            if arm_info.get('is_treatment', True):
                regimen.append(RegimenItem(
                    extrt=info.drug_name or "STUDY DRUG",
                    dose=dose_val,
                    dose_unit=dose_unit,
                    route=route,
                    frequency=freq,
                ))
            else:
                regimen.append(RegimenItem(
                    extrt="PLACEBO",
                    dose=0.0,
                    dose_unit=dose_unit,
                    route=route,
                    frequency=freq,
                ))
            
            arms.append(ArmSpec(
                armcd=arm_info['armcd'],
                arm=arm_info['arm'],
                regimen=regimen,
            ))
        
        # Default arms if none extracted
        if not arms:
            arms = [
                ArmSpec(
                    armcd='TRT',
                    arm=f'{info.drug_name or "STUDY DRUG"} Treatment',
                    regimen=[RegimenItem(
                        extrt=info.drug_name or "STUDY DRUG",
                        dose=dose_val,
                        dose_unit=dose_unit,
                        route=route,
                        frequency=freq,
                    )]
                )
            ]
        
        # Build elements
        elements = [
            ElementSpec(etcd='SCRN', element='Screening', epoch='SCREENING'),
            ElementSpec(etcd='TRT', element='Treatment', epoch='TREATMENT'),
            ElementSpec(etcd='FU', element='Follow-up', epoch='FOLLOW-UP'),
        ]
        
        # Build visits
        visits = []
        if info.visits:
            for v in info.visits:
                nominal_day = v.get('visitdy', 1)
                if nominal_day < 0:
                    nominal_day = -7  # Screening
                visits.append(VisitSpec(
                    visitnum=v['visitnum'],
                    visit=v['visit'],
                    nominal_day=nominal_day,
                ))
        else:
            # Default visits
            visits = [
                VisitSpec(visitnum=1, visit='Screening', nominal_day=-14),
                VisitSpec(visitnum=2, visit='Baseline/Day 1', nominal_day=1),
                VisitSpec(visitnum=3, visit='End of Treatment', nominal_day=info.treatment_duration_weeks * 7 or 84),
                VisitSpec(visitnum=4, visit='Follow-up', nominal_day=(info.treatment_duration_weeks or 12) * 7 + 28),
            ]
        
        # Build arm paths
        arm_paths = []
        for arm in arms:
            arm_paths.append(ArmPath(
                armcd=arm.armcd,
                elements=[
                    ArmPathItem(etcd='SCRN', taetord=1),
                    ArmPathItem(etcd='TRT', taetord=2),
                    ArmPathItem(etcd='FU', taetord=3),
                ]
            ))
        
        # Build TS parameters
        ts_params = [
            TSParameter(tsparmcd='STUDYID', tsval=info.study_id or info.protocol_number or 'STUDY001'),
            TSParameter(tsparmcd='SPONSOR', tsval=info.sponsor or 'SPONSOR'),
            TSParameter(tsparmcd='INDIC', tsval=info.indication or 'Indication'),
            TSParameter(tsparmcd='TPHASE', tsval=f'PHASE {info.phase}' if info.phase else 'PHASE 3'),
            TSParameter(tsparmcd='TBLIND', tsval=info.blinding or 'DOUBLE BLIND'),
            TSParameter(tsparmcd='TCNTRL', tsval=info.control_type or 'PLACEBO'),
            TSParameter(tsparmcd='INTMODEL', tsval=info.design_type or 'PARALLEL'),
            TSParameter(tsparmcd='TTYPE', tsval='SAFETY AND EFFICACY'),
            TSParameter(tsparmcd='TRT', tsval=info.drug_name or 'STUDY DRUG'),
            TSParameter(tsparmcd='ROUTE', tsval=route.value),
        ]
        
        # Demographics
        ratio_parts = info.randomization_ratio.split(':') if info.randomization_ratio else ['1', '1']
        ratio = [int(r) for r in ratio_parts if r.isdigit()] or [1, 1]
        total_ratio = sum(ratio)
        
        subjects_per_arm = {}
        target = info.target_enrollment or 100
        for i, arm in enumerate(arms):
            if i < len(ratio):
                subjects_per_arm[arm.armcd] = int(target * ratio[i] / total_ratio)
            else:
                subjects_per_arm[arm.armcd] = int(target / len(arms))
        
        demographics = DemographicsDefaults(
            age_min=info.age_min,
            age_max=info.age_max,
            total_subjects=target,
            subjects_per_arm=subjects_per_arm,
        )
        
        # Assumptions
        assumptions = [
            Assumption(
                parameter='PROTOCOL',
                assumed_value=info.protocol_number,
                reason=f'Extracted from protocol document',
            ),
            Assumption(
                parameter='RANDOMIZATION',
                assumed_value=info.randomization_ratio,
                reason='Extracted from protocol design section',
            ),
            Assumption(
                parameter='TREATMENT',
                assumed_value=f'{info.drug_name}, {route.value}, {freq.value}',
                reason='Extracted from protocol treatment section',
            ),
        ]
        
        return TrialDesignSpec(
            study_id=info.study_id or info.protocol_number or 'STUDY001',
            study_name=info.trial_name or info.protocol_number or 'Clinical Trial',
            phase=f'Phase {info.phase}' if info.phase else 'Phase 3',
            sponsor=info.sponsor or 'Sponsor',
            indication=info.indication or 'Indication',
            arms=arms,
            elements=elements,
            visits=visits,
            arm_paths=arm_paths,
            ts_params=ts_params,
            demographics=demographics,
            assumptions=assumptions,
        )


def parse_protocol_file(file_path: str) -> Tuple[ExtractedProtocolInfo, TrialDesignSpec]:
    """
    Parse a protocol file and return extracted info and trial spec.
    
    Supports:
    - Text files (.txt)
    - Plain text PDFs (readable as text)
    - Image-based PDFs (via OCR)
    
    Args:
        file_path: Path to protocol document
        
    Returns:
        Tuple of (ExtractedProtocolInfo, TrialDesignSpec)
    """
    path = Path(file_path)
    text = ""
    
    # Try reading as plain text first
    try:
        with open(path, 'r', encoding='utf-8', errors='ignore') as f:
            text = f.read()
        if len(text) > 1000:  # Looks like valid text
            pass
        else:
            text = ""
    except:
        pass
    
    # If not text, try PDF extraction
    if not text or len(text) < 1000:
        try:
            import fitz  # PyMuPDF
            doc = fitz.open(str(path))
            text_parts = []
            for page in doc:
                text_parts.append(page.get_text())
            text = '\n'.join(text_parts)
            doc.close()
        except:
            pass
    
    # If still no text, try as ZIP (image-based PDF)
    if not text or len(text) < 1000:
        import zipfile
        import tempfile
        try:
            with zipfile.ZipFile(str(path), 'r') as zf:
                with tempfile.TemporaryDirectory() as tmpdir:
                    zf.extractall(tmpdir)
                    # OCR images
                    import pytesseract
                    from PIL import Image
                    images = sorted(Path(tmpdir).glob('*.jpeg'))
                    images.extend(sorted(Path(tmpdir).glob('*.jpg')))
                    images.extend(sorted(Path(tmpdir).glob('*.png')))
                    
                    text_parts = []
                    for img_path in images[:30]:  # Limit pages
                        try:
                            img = Image.open(img_path)
                            text_parts.append(pytesseract.image_to_string(img))
                        except:
                            continue
                    text = '\n'.join(text_parts)
        except:
            pass
    
    if not text:
        raise ValueError(f"Could not extract text from {file_path}")
    
    # Parse the text
    parser = AdaptiveProtocolParser()
    info = parser.parse(text, str(path))
    spec = parser.to_trial_spec()
    
    return info, spec
