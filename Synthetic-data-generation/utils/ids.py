"""
ID generation utilities for SDTM data.
"""

from typing import Dict, Optional, List


# Track sequence numbers per subject per domain
_SEQ_COUNTERS: Dict[str, Dict[str, int]] = {}


def generate_usubjid(study_id: str, site_id: str, subject_num: int) -> str:
    """
    Generate a unique subject identifier.
    
    Format: {STUDYID}-{SITEID}-{SUBJID}
    """
    subjid = f"{subject_num:04d}"
    return f"{study_id}-{site_id}-{subjid}"


def generate_subjid(subject_num: int) -> str:
    """Generate subject ID within site."""
    return f"{subject_num:04d}"


def generate_seq(usubjid: str, domain: str) -> int:
    """
    Generate next sequence number for a subject in a domain.
    
    Ensures --SEQ is unique within USUBJID for each domain.
    """
    global _SEQ_COUNTERS
    
    if usubjid not in _SEQ_COUNTERS:
        _SEQ_COUNTERS[usubjid] = {}
    
    if domain not in _SEQ_COUNTERS[usubjid]:
        _SEQ_COUNTERS[usubjid][domain] = 0
    
    _SEQ_COUNTERS[usubjid][domain] += 1
    return _SEQ_COUNTERS[usubjid][domain]


def reset_seq_counters() -> None:
    """Reset all sequence counters."""
    global _SEQ_COUNTERS
    _SEQ_COUNTERS = {}


def reset_subject_seq(usubjid: str) -> None:
    """Reset sequence counters for a specific subject."""
    global _SEQ_COUNTERS
    if usubjid in _SEQ_COUNTERS:
        _SEQ_COUNTERS[usubjid] = {}


class SubjectIDGenerator:
    """
    Generates unique subject identifiers.
    
    Format: {STUDYID}-{SITEID}-{SUBJID} (globally unique across all studies)
    
    SUBJID must be unique across the entire study (not just within a site).
    """
    
    def __init__(self, study_id: str, n_sites: int = 3):
        self.study_id = study_id
        self.n_sites = n_sites
        self._global_counter: int = 0  # Global subject counter for unique SUBJID
        self._site_ids: Dict[int, str] = {}
        
        # Pre-generate shorter site IDs (S01, S02, S03)
        for i in range(n_sites):
            self._site_ids[i] = f"S{i+1:02d}"
    
    def generate_usubjid(self, site_idx: int) -> str:
        """
        Generate USUBJID for a subject at a given site.
        
        Format: {STUDYID}-{SITEID}-{SUBJID} (globally unique)
        SUBJID is globally unique across the study, not per site.
        """
        if site_idx not in self._site_ids:
            site_idx = site_idx % self.n_sites
        
        site_id = self._site_ids[site_idx]
        self._global_counter += 1
        subject_num = self._global_counter  # Globally unique
        
        return f"{self.study_id}-{site_id}-{subject_num:03d}"
    
    def get_subjid_from_usubjid(self, usubjid: str) -> str:
        """Extract SUBJID from USUBJID."""
        parts = usubjid.split('-')
        if len(parts) >= 1:
            return parts[-1]
        return usubjid
    
    def get_siteid_from_usubjid(self, usubjid: str) -> str:
        """Extract SITEID from USUBJID."""
        parts = usubjid.split('-')
        if len(parts) >= 2:
            return parts[-2]  # Second to last part
        return "S01"


class SequenceTracker:
    """
    Tracks sequence numbers for SDTM --SEQ variables.
    
    Maintains unique sequence counters per subject per domain.
    """
    
    def __init__(self):
        self._counters: Dict[str, Dict[str, int]] = {}
    
    def get_next_seq(self, domain: str, usubjid: str) -> int:
        """
        Get next sequence number for a subject in a domain.
        
        Args:
            domain: SDTM domain code (e.g., 'AE', 'CM')
            usubjid: Subject identifier
            
        Returns:
            Next sequence number (starting from 1)
        """
        if usubjid not in self._counters:
            self._counters[usubjid] = {}
        
        if domain not in self._counters[usubjid]:
            self._counters[usubjid][domain] = 0
        
        self._counters[usubjid][domain] += 1
        return self._counters[usubjid][domain]
    
    def get_current_seq(self, domain: str, usubjid: str) -> int:
        """Get current sequence number without incrementing."""
        if usubjid not in self._counters:
            return 0
        if domain not in self._counters[usubjid]:
            return 0
        return self._counters[usubjid][domain]
    
    def reset_domain(self, domain: str) -> None:
        """Reset sequence counters for a domain."""
        for usubjid in self._counters:
            if domain in self._counters[usubjid]:
                self._counters[usubjid][domain] = 0
    
    def reset_all(self) -> None:
        """Reset all sequence counters."""
        self._counters = {}


class InvestigatorNameGenerator:
    """
    Generates consistent investigator names for sites.
    
    Each site gets a deterministic investigator name.
    """
    
    FIRST_NAMES = [
        "James", "Mary", "John", "Patricia", "Robert", "Jennifer",
        "Michael", "Linda", "William", "Elizabeth", "David", "Barbara",
        "Richard", "Susan", "Joseph", "Jessica", "Thomas", "Sarah"
    ]
    
    LAST_NAMES = [
        "Smith", "Johnson", "Williams", "Brown", "Jones", "Garcia",
        "Miller", "Davis", "Rodriguez", "Martinez", "Hernandez", "Lopez",
        "Gonzalez", "Wilson", "Anderson", "Thomas", "Taylor", "Moore"
    ]
    
    def __init__(self):
        self._site_investigators: Dict[str, str] = {}
    
    def get_investigator_name(self, siteid: str, rng=None) -> str:
        """
        Get investigator name for a site.
        
        Uses consistent name for each site.
        """
        if siteid not in self._site_investigators:
            # Generate deterministic name based on site ID
            site_hash = hash(siteid) % 1000
            first_idx = site_hash % len(self.FIRST_NAMES)
            last_idx = (site_hash // len(self.FIRST_NAMES)) % len(self.LAST_NAMES)
            
            first = self.FIRST_NAMES[first_idx]
            last = self.LAST_NAMES[last_idx]
            self._site_investigators[siteid] = f"Dr. {first} {last}"
        
        return self._site_investigators[siteid]
