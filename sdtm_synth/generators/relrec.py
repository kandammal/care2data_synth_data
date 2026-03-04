"""
SDTM Synthetic Data Generator - Related Records (RELREC) Generator

This module generates the RELREC special-purpose dataset that defines
relationships between records across domains per SDTM-IG Section 8.2.

Per SDTM-IG Section 8.2 (Relating Peer Records):
- Each related record gets a row in RELREC
- USUBJID identifies the subject
- IDVAR identifies the variable used (--SEQ, --GRPID, etc.)
- IDVARVAL contains the value of that variable
- Same RELID groups related records together
"""

from __future__ import annotations
from typing import List, Dict, Any, Optional
import pandas as pd

from ..spec.models import TrialDesignSpec


class RelatedRecordsGenerator:
    """
    Generates the Related Records (RELREC) special-purpose dataset.
    
    Per SDTM-IG Section 8.2.2 Example 1:
    - AE with AESEQ=5 related to CM with CMSEQ=11 and CMSEQ=12:
      Row 1: RDOMAIN=AE, USUBJID=123456, IDVAR=AESEQ, IDVARVAL=5, RELID=1
      Row 2: RDOMAIN=CM, USUBJID=123456, IDVAR=CMSEQ, IDVARVAL=11, RELID=1
      Row 3: RDOMAIN=CM, USUBJID=123456, IDVAR=CMSEQ, IDVARVAL=12, RELID=1
    """
    
    def __init__(self, spec: TrialDesignSpec):
        """
        Initialize the generator.
        
        Args:
            spec: Trial design specification
        """
        self.spec = spec
        self.relationships: List[Dict[str, Any]] = []
        self.relid_counter = 0
    
    def add_peer_record_relationship(
        self,
        usubjid: str,
        records: List[Dict[str, Any]]
    ) -> str:
        """
        Add a peer record relationship per SDTM-IG Section 8.2.
        
        Args:
            usubjid: Subject identifier
            records: List of dicts with 'rdomain', 'idvar', 'idvarval' keys
        
        Returns:
            RELID for this relationship
        """
        self.relid_counter += 1
        relid = str(self.relid_counter)
        
        for rec in records:
            self.relationships.append({
                'STUDYID': self.spec.study_id,
                'RDOMAIN': rec['rdomain'],
                'USUBJID': usubjid,
                'IDVAR': rec['idvar'],
                'IDVARVAL': str(rec['idvarval']),
                'RELTYPE': '',  # RELTYPE only used for dataset-to-dataset (Section 8.3)
                'RELID': relid,
            })
        
        return relid
    
    def add_ae_ds_death_relationship(
        self,
        usubjid: str,
        aeseq: int,
        dsseq: int
    ) -> str:
        """
        Add relationship between a fatal AE and DS DEATH record.
        
        Per SDTM-IG Section 8.2: Uses --SEQ to identify specific records.
        
        Args:
            usubjid: Subject identifier
            aeseq: AESEQ value of fatal AE
            dsseq: DSSEQ value of DEATH disposition record
        
        Returns:
            RELID for this relationship
        """
        return self.add_peer_record_relationship(
            usubjid=usubjid,
            records=[
                {'rdomain': 'AE', 'idvar': 'AESEQ', 'idvarval': aeseq},
                {'rdomain': 'DS', 'idvar': 'DSSEQ', 'idvarval': dsseq},
            ]
        )
    
    def add_ae_cm_relationship(
        self,
        usubjid: str,
        aeseq: int,
        cmseq_list: List[int]
    ) -> str:
        """
        Add relationship between an AE and CM(s) taken to treat it.
        
        Per SDTM-IG Section 8.2 Example 1.
        
        Args:
            usubjid: Subject identifier
            aeseq: AESEQ value
            cmseq_list: List of CMSEQ values for medications treating this AE
        
        Returns:
            RELID for this relationship
        """
        records = [{'rdomain': 'AE', 'idvar': 'AESEQ', 'idvarval': aeseq}]
        for cmseq in cmseq_list:
            records.append({'rdomain': 'CM', 'idvar': 'CMSEQ', 'idvarval': cmseq})
        
        return self.add_peer_record_relationship(usubjid=usubjid, records=records)
    
    def generate(self) -> pd.DataFrame:
        """
        Generate RELREC dataset from collected relationships.
        
        Returns:
            RELREC DataFrame
        """
        if not self.relationships:
            return self._empty_relrec()
        
        df = pd.DataFrame(self.relationships)
        
        # Sort by USUBJID, RELID, RDOMAIN
        df = df.sort_values(['USUBJID', 'RELID', 'RDOMAIN']).reset_index(drop=True)
        
        cols = ['STUDYID', 'RDOMAIN', 'USUBJID', 'IDVAR', 'IDVARVAL', 'RELTYPE', 'RELID']
        return df[cols]
    
    def _empty_relrec(self) -> pd.DataFrame:
        """Return empty RELREC DataFrame."""
        return pd.DataFrame(columns=[
            'STUDYID', 'RDOMAIN', 'USUBJID', 'IDVAR', 'IDVARVAL', 'RELTYPE', 'RELID'
        ])
