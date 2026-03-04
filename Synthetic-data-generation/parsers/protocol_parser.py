"""
Adaptive Protocol Parser

Automatically extracts trial design parameters from protocol documents
and generates appropriate TrialDesignSpec for SDTM data generation.
"""

import re
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path


class StudyPhase(Enum):
    PHASE_1 = "1"
    PHASE_1_2 = "1/2"
    PHASE_2 = "2"
    PHASE_2_3 = "2/3"
    PHASE_3 = "3"
    PHASE_4 = "4"


class StudyDesign(Enum):
    PARALLEL = "parallel"
    CROSSOVER = "crossover"
    SINGLE_ARM = "single_arm"
    FACTORIAL = "factorial"


class BlindingType(Enum):
    OPEN_LABEL = "open_label"
    SINGLE_BLIND = "single_blind"
    DOUBLE_BLIND = "double_blind"


@dataclass
class TreatmentArm:
    """Represents a treatment arm in the study."""
    name: str
    drug_name: str
    dose: Optional[float] = None
    dose_unit: str = "mg"
    route: str = "INTRAVENOUS"
    frequency: str = "Q2W"
    is_placebo: bool = False
    n_subjects: Optional[int] = None
    ratio: int = 1  # For randomization ratio


@dataclass 
class VisitSchedule:
    """Represents a visit in the study schedule."""
    visit_num: int
    visit_name: str
    day: int
    week: Optional[int] = None
    window_days: int = 3
    is_dosing_visit: bool = False


@dataclass
class ParsedProtocol:
    """Structured representation of a parsed protocol."""
    # Identifiers
    protocol_id: str
    protocol_title: str
    sponsor: str = ""
    
    # Study design
    phase: StudyPhase = StudyPhase.PHASE_2
    design: StudyDesign = StudyDesign.PARALLEL
    blinding: BlindingType = BlindingType.DOUBLE_BLIND
    
    # Population
    indication: str = ""
    age_min: int = 18
    age_max: int = 75
    target_enrollment: int = 100
    
    # Treatment
    treatment_arms: List[TreatmentArm] = field(default_factory=list)
    treatment_duration_weeks: int = 12
    follow_up_weeks: int = 4
    
    # Visits
    visits: List[VisitSchedule] = field(default_factory=list)
    
    # Drug info
    investigational_product: str = ""
    ip_route: str = "INTRAVENOUS"
    ip_dosage_form: str = "INJECTION"
    
    # Extracted raw data
    raw_text: str = ""
    confidence_score: float = 0.0


class ProtocolParser:
    """
    Adaptive parser that extracts trial design from protocol text.
    
    Works with:
    - Plain text protocol documents
    - OCR-extracted text from scanned PDFs
    - Structured protocol synopses
    """
    
    def __init__(self):
        self.patterns = self._compile_patterns()
    
    def _compile_patterns(self) -> Dict[str, re.Pattern]:
        """Compile regex patterns for extraction."""
        return {
            # Protocol identifiers
            'protocol_id': re.compile(
                r'(?:protocol\s*(?:number|no\.?|#)?[:\s]*|study\s*(?:number|no\.?)?[:\s]*)([A-Z0-9]+-?[A-Z0-9-]+)',
                re.IGNORECASE
            ),
            
            # Phase detection
            'phase': re.compile(
                r'phase\s*([1-4](?:/[1-4])?|[IViv]+(?:/[IViv]+)?)',
                re.IGNORECASE
            ),
            
            # Blinding
            'double_blind': re.compile(r'double[- ]?blind', re.IGNORECASE),
            'single_blind': re.compile(r'single[- ]?blind', re.IGNORECASE),
            'open_label': re.compile(r'open[- ]?label', re.IGNORECASE),
            
            # Randomization ratio
            'ratio_2_1': re.compile(r'2\s*:\s*1\s*(?:ratio|random)', re.IGNORECASE),
            'ratio_1_1': re.compile(r'1\s*:\s*1\s*(?:ratio|random)', re.IGNORECASE),
            'ratio_1_1_1': re.compile(r'1\s*:\s*1\s*:\s*1', re.IGNORECASE),
            
            # Sample size
            'n_subjects': re.compile(
                r'(?:approximately|~|about|up to)?\s*(\d{2,4})\s*(?:participants?|patients?|subjects?)',
                re.IGNORECASE
            ),
            
            # Age range
            'age_range': re.compile(
                r'(\d{1,2})\s*(?:to|-)\s*(\d{1,2})\s*years?\s*(?:of\s*age|old)?',
                re.IGNORECASE
            ),
            'age_pediatric': re.compile(
                r'(?:children|adolescents?|pediatric)',
                re.IGNORECASE
            ),
            
            # Duration
            'duration_weeks': re.compile(
                r'(\d{1,3})\s*(?:-?\s*)?week(?:s)?\s*(?:treatment|study|duration)',
                re.IGNORECASE
            ),
            'duration_months': re.compile(
                r'(\d{1,2})\s*(?:-?\s*)?month(?:s)?\s*(?:treatment|study|duration)',
                re.IGNORECASE
            ),
            
            # Dosing frequency
            'freq_qd': re.compile(r'\bQ\.?D\.?\b|once\s*daily', re.IGNORECASE),
            'freq_bid': re.compile(r'\bB\.?I\.?D\.?\b|twice\s*daily', re.IGNORECASE),
            'freq_qw': re.compile(r'\bQ\.?W\.?\b|once\s*weekly|weekly', re.IGNORECASE),
            'freq_q2w': re.compile(r'\bQ\.?2\.?W\.?\b|every\s*(?:2|two)\s*weeks?|biweekly', re.IGNORECASE),
            'freq_q4w': re.compile(r'\bQ\.?4\.?W\.?\b|every\s*(?:4|four)\s*weeks?|monthly', re.IGNORECASE),
            
            # Route
            'route_iv': re.compile(r'\b(?:IV|intravenous(?:ly)?|infusion)\b', re.IGNORECASE),
            'route_sc': re.compile(r'\b(?:SC|subcutaneous(?:ly)?)\b', re.IGNORECASE),
            'route_oral': re.compile(r'\b(?:oral(?:ly)?|PO|tablet|capsule)\b', re.IGNORECASE),
            
            # Dose extraction
            'dose_mg': re.compile(
                r'(\d+(?:\.\d+)?)\s*(?:mg)(?:/(?:kg|m2|day))?',
                re.IGNORECASE
            ),
            'dose_ug': re.compile(
                r'(\d+(?:\.\d+)?)\s*(?:ug|mcg|μg)(?:/(?:kg|m2|day))?',
                re.IGNORECASE
            ),
            
            # Placebo detection
            'placebo': re.compile(r'\bplacebo\b', re.IGNORECASE),
            'placebo_controlled': re.compile(r'placebo[- ]?controlled', re.IGNORECASE),
            
            # Treatment arms
            'arm_pattern': re.compile(
                r'(?:arm|group|cohort)\s*(?:[A-Z]|\d+|one|two|three)?[:\s]+(.+?)(?:\n|$)',
                re.IGNORECASE
            ),
        }
    
    def parse(self, text: str, protocol_id: str = None) -> ParsedProtocol:
        """
        Parse protocol text and extract trial design parameters.
        
        Args:
            text: Raw protocol text (can be from OCR)
            protocol_id: Optional protocol ID override
            
        Returns:
            ParsedProtocol with extracted parameters
        """
        # Clean text
        text = self._clean_text(text)
        
        # Initialize parsed protocol
        parsed = ParsedProtocol(
            protocol_id=protocol_id or self._extract_protocol_id(text),
            protocol_title=self._extract_title(text),
            raw_text=text[:5000]  # Store first 5000 chars for reference
        )
        
        # Extract study design parameters
        parsed.phase = self._extract_phase(text)
        parsed.blinding = self._extract_blinding(text)
        parsed.design = self._extract_design(text)
        
        # Extract population parameters
        age_min, age_max = self._extract_age_range(text)
        parsed.age_min = age_min
        parsed.age_max = age_max
        parsed.target_enrollment = self._extract_sample_size(text)
        parsed.indication = self._extract_indication(text)
        
        # Extract treatment parameters
        parsed.treatment_duration_weeks = self._extract_duration(text)
        parsed.ip_route = self._extract_route(text)
        parsed.treatment_arms = self._extract_arms(text)
        
        # Extract visit schedule
        parsed.visits = self._extract_visits(text)
        
        # Calculate confidence
        parsed.confidence_score = self._calculate_confidence(parsed)
        
        return parsed
    
    def _clean_text(self, text: str) -> str:
        """Clean and normalize text."""
        # Remove excessive whitespace
        text = re.sub(r'\s+', ' ', text)
        # Fix common OCR errors
        text = text.replace('|', 'I').replace('0', 'O')
        return text.strip()
    
    def _extract_protocol_id(self, text: str) -> str:
        """Extract protocol identifier."""
        match = self.patterns['protocol_id'].search(text)
        if match:
            return match.group(1).strip()
        return "UNKNOWN"
    
    def _extract_title(self, text: str) -> str:
        """Extract protocol title."""
        # Look for title patterns
        title_patterns = [
            r'(?:protocol\s*title|title)[:\s]*(.+?)(?:\n|protocol\s*number)',
            r'A\s+Phase\s+[0-9IViv]+[^.]+Study[^.]+\.',
        ]
        for pattern in title_patterns:
            match = re.search(pattern, text, re.IGNORECASE | re.DOTALL)
            if match:
                title = match.group(1) if match.lastindex else match.group(0)
                return title.strip()[:200]  # Limit length
        return "Clinical Trial Protocol"
    
    def _extract_phase(self, text: str) -> StudyPhase:
        """Extract study phase."""
        match = self.patterns['phase'].search(text)
        if match:
            phase_str = match.group(1).upper()
            # Convert Roman numerals
            phase_str = phase_str.replace('IV', '4').replace('III', '3').replace('II', '2').replace('I', '1')
            if '1/2' in phase_str or '1-2' in phase_str:
                return StudyPhase.PHASE_1_2
            elif '2/3' in phase_str or '2-3' in phase_str:
                return StudyPhase.PHASE_2_3
            elif '3' in phase_str:
                return StudyPhase.PHASE_3
            elif '2' in phase_str:
                return StudyPhase.PHASE_2
            elif '4' in phase_str:
                return StudyPhase.PHASE_4
            elif '1' in phase_str:
                return StudyPhase.PHASE_1
        return StudyPhase.PHASE_2  # Default
    
    def _extract_blinding(self, text: str) -> BlindingType:
        """Extract blinding type."""
        if self.patterns['double_blind'].search(text):
            return BlindingType.DOUBLE_BLIND
        elif self.patterns['single_blind'].search(text):
            return BlindingType.SINGLE_BLIND
        elif self.patterns['open_label'].search(text):
            return BlindingType.OPEN_LABEL
        return BlindingType.DOUBLE_BLIND  # Default for RCTs
    
    def _extract_design(self, text: str) -> StudyDesign:
        """Extract study design type."""
        if re.search(r'crossover', text, re.IGNORECASE):
            return StudyDesign.CROSSOVER
        elif re.search(r'factorial', text, re.IGNORECASE):
            return StudyDesign.FACTORIAL
        elif re.search(r'single[- ]?(?:arm|group|treatment)', text, re.IGNORECASE):
            return StudyDesign.SINGLE_ARM
        return StudyDesign.PARALLEL
    
    def _extract_age_range(self, text: str) -> Tuple[int, int]:
        """Extract age range."""
        match = self.patterns['age_range'].search(text)
        if match:
            age_min = int(match.group(1))
            age_max = int(match.group(2))
            return age_min, age_max
        
        # Check for pediatric indication
        if self.patterns['age_pediatric'].search(text):
            return 8, 17
        
        return 18, 75  # Default adult range
    
    def _extract_sample_size(self, text: str) -> int:
        """Extract target enrollment."""
        matches = self.patterns['n_subjects'].findall(text)
        if matches:
            # Return the largest number found (likely total enrollment)
            return max(int(n) for n in matches)
        return 100  # Default
    
    def _extract_duration(self, text: str) -> int:
        """Extract treatment duration in weeks."""
        # Try weeks first
        match = self.patterns['duration_weeks'].search(text)
        if match:
            return int(match.group(1))
        
        # Try months
        match = self.patterns['duration_months'].search(text)
        if match:
            return int(match.group(1)) * 4  # Convert to weeks
        
        return 12  # Default
    
    def _extract_route(self, text: str) -> str:
        """Extract route of administration."""
        if self.patterns['route_iv'].search(text):
            return "INTRAVENOUS"
        elif self.patterns['route_sc'].search(text):
            return "SUBCUTANEOUS"
        elif self.patterns['route_oral'].search(text):
            return "ORAL"
        return "INTRAVENOUS"  # Default for biologics
    
    def _extract_indication(self, text: str) -> str:
        """Extract therapeutic indication."""
        indication_patterns = [
            r'(?:indication|disease|condition)[:\s]*([A-Za-z\s]+?)(?:\n|$)',
            r'patients?\s+with\s+([A-Za-z\s]+?)(?:\.|,|\n)',
            r'(?:active|newly\s+diagnosed)\s+([A-Za-z\s]+?)(?:\.|,|\n)',
        ]
        for pattern in indication_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                indication = match.group(1).strip()
                if len(indication) > 5:
                    return indication[:100]
        return "Clinical Condition"
    
    def _extract_arms(self, text: str) -> List[TreatmentArm]:
        """Extract treatment arms."""
        arms = []
        
        # Check for placebo-controlled
        has_placebo = self.patterns['placebo_controlled'].search(text) is not None
        
        # Detect randomization ratio
        if self.patterns['ratio_1_1_1'].search(text):
            # 3 arms (1:1:1)
            ratios = [1, 1, 1]
        elif self.patterns['ratio_2_1'].search(text):
            # 2 arms (2:1)
            ratios = [2, 1]
        else:
            # Default 1:1
            ratios = [1, 1]
        
        # Extract doses
        doses = self.patterns['dose_mg'].findall(text)
        unique_doses = sorted(set(float(d) for d in doses), reverse=True)[:3]
        
        # Determine frequency
        if self.patterns['freq_q2w'].search(text):
            freq = "Q2W"
        elif self.patterns['freq_q4w'].search(text):
            freq = "Q4W"
        elif self.patterns['freq_qw'].search(text):
            freq = "QW"
        elif self.patterns['freq_bid'].search(text):
            freq = "BID"
        elif self.patterns['freq_qd'].search(text):
            freq = "QD"
        else:
            freq = "Q2W"  # Default for biologics
        
        route = self._extract_route(text)
        
        # Build arms based on detected pattern
        if len(ratios) == 3 and len(unique_doses) >= 2:
            # 3-arm dose-finding study
            arms.append(TreatmentArm(
                name="HIGH_DOSE",
                drug_name="STUDY_DRUG",
                dose=unique_doses[0],
                route=route,
                frequency=freq,
                ratio=ratios[0]
            ))
            arms.append(TreatmentArm(
                name="LOW_DOSE", 
                drug_name="STUDY_DRUG",
                dose=unique_doses[1] if len(unique_doses) > 1 else unique_doses[0] / 2,
                route=route,
                frequency=freq,
                ratio=ratios[1]
            ))
            arms.append(TreatmentArm(
                name="PLACEBO",
                drug_name="PLACEBO",
                dose=0,
                route=route,
                frequency=freq,
                is_placebo=True,
                ratio=ratios[2]
            ))
        elif has_placebo:
            # 2-arm placebo-controlled
            dose = unique_doses[0] if unique_doses else 100
            arms.append(TreatmentArm(
                name="ACTIVE",
                drug_name="STUDY_DRUG",
                dose=dose,
                route=route,
                frequency=freq,
                ratio=ratios[0]
            ))
            arms.append(TreatmentArm(
                name="PLACEBO",
                drug_name="PLACEBO",
                dose=0,
                route=route,
                frequency=freq,
                is_placebo=True,
                ratio=ratios[1] if len(ratios) > 1 else 1
            ))
        else:
            # Single arm
            dose = unique_doses[0] if unique_doses else 100
            arms.append(TreatmentArm(
                name="TREATMENT",
                drug_name="STUDY_DRUG",
                dose=dose,
                route=route,
                frequency=freq,
                ratio=1
            ))
        
        return arms
    
    def _extract_visits(self, text: str) -> List[VisitSchedule]:
        """Extract visit schedule."""
        visits = []
        
        # Look for visit patterns
        visit_patterns = [
            r'(?:visit|day)\s*(\d+)[:\s]*(?:week\s*)?(\d+)?',
            r'week\s*(\d+)',
            r'day\s*(\d+)',
        ]
        
        found_days = set()
        for pattern in visit_patterns:
            for match in re.finditer(pattern, text, re.IGNORECASE):
                day = int(match.group(1))
                if day not in found_days and day <= 365:
                    found_days.add(day)
        
        # Generate visit schedule
        if found_days:
            for i, day in enumerate(sorted(found_days)[:20], 1):
                visits.append(VisitSchedule(
                    visit_num=i,
                    visit_name=f"VISIT {i}",
                    day=day,
                    week=day // 7 if day > 0 else 0
                ))
        else:
            # Generate default schedule based on duration
            duration = self._extract_duration(text)
            visits = self._generate_default_visits(duration)
        
        return visits
    
    def _generate_default_visits(self, duration_weeks: int) -> List[VisitSchedule]:
        """Generate a default visit schedule."""
        visits = []
        
        # Screening
        visits.append(VisitSchedule(
            visit_num=1,
            visit_name="SCREENING",
            day=-14,
            week=-2
        ))
        
        # Baseline/Day 1
        visits.append(VisitSchedule(
            visit_num=2,
            visit_name="BASELINE",
            day=1,
            week=0,
            is_dosing_visit=True
        ))
        
        # Treatment visits (every 2 weeks for biologics)
        visit_num = 3
        for week in range(2, duration_weeks + 1, 2):
            visits.append(VisitSchedule(
                visit_num=visit_num,
                visit_name=f"WEEK {week}",
                day=week * 7,
                week=week,
                is_dosing_visit=True
            ))
            visit_num += 1
        
        # End of Treatment
        visits.append(VisitSchedule(
            visit_num=visit_num,
            visit_name="END_OF_TREATMENT",
            day=duration_weeks * 7,
            week=duration_weeks
        ))
        
        # Follow-up
        visits.append(VisitSchedule(
            visit_num=visit_num + 1,
            visit_name="FOLLOW_UP",
            day=(duration_weeks + 4) * 7,
            week=duration_weeks + 4
        ))
        
        return visits
    
    def _calculate_confidence(self, parsed: ParsedProtocol) -> float:
        """Calculate confidence score for the parsing."""
        score = 0.0
        
        # Protocol ID found
        if parsed.protocol_id != "UNKNOWN":
            score += 0.15
        
        # Phase detected
        if parsed.phase != StudyPhase.PHASE_2:  # Not just default
            score += 0.1
        
        # Arms detected
        if len(parsed.treatment_arms) > 0:
            score += 0.2
        
        # Sample size reasonable
        if 10 < parsed.target_enrollment < 10000:
            score += 0.15
        
        # Age range reasonable
        if parsed.age_min < parsed.age_max:
            score += 0.1
        
        # Duration reasonable
        if 1 <= parsed.treatment_duration_weeks <= 260:
            score += 0.1
        
        # Visits detected
        if len(parsed.visits) > 2:
            score += 0.2
        
        return min(score, 1.0)
    
    def to_trial_spec(self, parsed: ParsedProtocol) -> Dict[str, Any]:
        """
        Convert ParsedProtocol to TrialDesignSpec dictionary.
        
        This can be directly passed to generate_v2().
        """
        # Calculate subjects per arm based on ratios
        total_ratio = sum(arm.ratio for arm in parsed.treatment_arms)
        subjects_per_arm = {}
        for arm in parsed.treatment_arms:
            n = int(parsed.target_enrollment * arm.ratio / total_ratio)
            subjects_per_arm[arm.name] = max(n, 10)
        
        # Build arms spec
        arms = []
        for arm in parsed.treatment_arms:
            arm_spec = {
                'name': arm.name,
                'regimen': [{
                    'drug': arm.drug_name,
                    'dose': arm.dose,
                    'dose_unit': arm.dose_unit,
                    'frequency': arm.frequency,
                    'route': arm.route,
                    'duration_days': parsed.treatment_duration_weeks * 7
                }]
            }
            arms.append(arm_spec)
        
        # Build visits spec
        visits = []
        for v in parsed.visits:
            visit_spec = {
                'name': v.visit_name,
                'day': v.day,
                'window_before': v.window_days,
                'window_after': v.window_days,
            }
            visits.append(visit_spec)
        
        # Build complete spec
        spec = {
            'protocol_id': parsed.protocol_id,
            'study_title': parsed.protocol_title,
            'phase': parsed.phase.value,
            'blinding': parsed.blinding.value,
            'indication': parsed.indication,
            
            'arms': arms,
            'visits': visits,
            
            'demographics': {
                'age_min': parsed.age_min,
                'age_max': parsed.age_max,
                'total_subjects': parsed.target_enrollment,
                'subjects_per_arm': subjects_per_arm,
            },
            
            'treatment_duration_weeks': parsed.treatment_duration_weeks,
            'follow_up_weeks': parsed.follow_up_weeks,
        }
        
        return spec


def parse_protocol_file(file_path: str) -> ParsedProtocol:
    """
    Parse a protocol file (PDF, text, or ZIP with images).
    
    Args:
        file_path: Path to the protocol file
        
    Returns:
        ParsedProtocol object
    """
    from pathlib import Path
    import subprocess
    import tempfile
    
    path = Path(file_path)
    text = ""
    
    if path.suffix.lower() == '.pdf':
        # Check if it's actually a text file or ZIP
        with open(path, 'rb') as f:
            header = f.read(10)
        
        if header.startswith(b'PK'):
            # ZIP file (images)
            text = _ocr_zip_images(path)
        elif header[:4] == b'%PDF':
            # Real PDF
            text = _extract_pdf_text(path)
        else:
            # Plain text
            text = path.read_text(errors='ignore')
    
    elif path.suffix.lower() == '.txt':
        text = path.read_text(errors='ignore')
    
    elif path.suffix.lower() == '.zip':
        text = _ocr_zip_images(path)
    
    # Parse the extracted text
    parser = ProtocolParser()
    return parser.parse(text, protocol_id=path.stem)


def _extract_pdf_text(path: Path) -> str:
    """Extract text from a real PDF."""
    try:
        import fitz
        doc = fitz.open(str(path))
        text = ""
        for page in doc:
            text += page.get_text()
        doc.close()
        return text
    except Exception:
        # Fallback to pdftotext
        try:
            import subprocess
            result = subprocess.run(
                ['pdftotext', str(path), '-'],
                capture_output=True, text=True
            )
            return result.stdout
        except Exception:
            return ""


def _ocr_zip_images(path: Path) -> str:
    """OCR images from a ZIP file."""
    try:
        import zipfile
        import tempfile
        import pytesseract
        from PIL import Image
        
        text_parts = []
        with zipfile.ZipFile(path, 'r') as zf:
            # Sort by numeric filename
            files = sorted(
                [f for f in zf.namelist() if f.lower().endswith(('.jpg', '.jpeg', '.png'))],
                key=lambda x: int(''.join(filter(str.isdigit, x)) or 0)
            )
            
            with tempfile.TemporaryDirectory() as tmpdir:
                for f in files[:30]:  # Limit to first 30 pages
                    zf.extract(f, tmpdir)
                    img_path = Path(tmpdir) / f
                    img = Image.open(img_path)
                    text = pytesseract.image_to_string(img)
                    text_parts.append(text)
        
        return "\n\n".join(text_parts)
    except Exception as e:
        print(f"OCR error: {e}")
        return ""
