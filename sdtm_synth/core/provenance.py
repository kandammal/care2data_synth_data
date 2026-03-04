"""
Provenance Mapping — Contract 2

Maps canonical IDs to SDTM rows, enabling stable RELREC generation
even when SEQ values change due to re-sorting.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Optional, List, Dict, Tuple
import pandas as pd


@dataclass
class CanonicalRelationship:
    """A typed relationship between two canonical objects."""
    rel_id: str             # f"{source_id}|{target_id}|{type}|{ordinal}"
    source_id: str          # canonical ID of source (e.g., "SUBJ_0/AE_CAND_7")
    target_id: str          # canonical ID of target (e.g., "SUBJ_0/DS_DEATH")
    relationship_type: str  # "AE_CAUSES_DS" | "AE_FATAL_TO_DS" | "AE_TREATED_BY_CM" | "AE_FATAL_TO_DM"
    ordinal: int = 0
    usubjid: str = ""       # P0 fix: store USUBJID for cross-subject filtering in RELREC


class ProvenanceMap:
    """
    Bidirectional mapping between canonical IDs and SDTM (domain, USUBJID, SEQ) tuples.
    """

    def __init__(self):
        self._canonical_to_sdtm: Dict[str, List[Tuple[str, str, int]]] = {}
        self._sdtm_to_canonical: Dict[Tuple[str, str, int], str] = {}

    def register(self, canonical_id: str, domain: str, usubjid: str, seq: int):
        """Register a mapping from canonical ID to SDTM row."""
        key = (domain, usubjid, seq)
        if canonical_id not in self._canonical_to_sdtm:
            self._canonical_to_sdtm[canonical_id] = []
        self._canonical_to_sdtm[canonical_id].append(key)
        self._sdtm_to_canonical[key] = canonical_id

    def get_sdtm_rows(self, canonical_id: str) -> List[Tuple[str, str, int]]:
        """Get all SDTM rows for a canonical ID."""
        return self._canonical_to_sdtm.get(canonical_id, [])

    def get_canonical_id(self, domain: str, usubjid: str, seq: int) -> Optional[str]:
        """Get canonical ID for an SDTM row."""
        return self._sdtm_to_canonical.get((domain, usubjid, seq))

    def rebuild_relrec(
        self,
        relationships: List[CanonicalRelationship],
        study_id: str,
    ) -> pd.DataFrame:
        """
        Build RELREC from canonical relationships + current SEQ assignments.

        Two rows per relationship (reciprocal), sharing RELID.
        IDVARVAL resolved through provenance at render time.
        
        P0 fix: uses rel.usubjid to filter rows to the correct subject,
        preventing cross-subject linkage when canonical IDs collide.
        """
        records = []

        for rel in relationships:
            # Skip non-RELREC relationships (e.g., AE_FATAL_TO_DM)
            if rel.relationship_type == "AE_FATAL_TO_DM":
                continue

            source_rows = self.get_sdtm_rows(rel.source_id)
            target_rows = self.get_sdtm_rows(rel.target_id)

            if not source_rows or not target_rows:
                continue

            # P0 fix: filter rows by USUBJID when available
            if rel.usubjid:
                source_rows = [r for r in source_rows if r[1] == rel.usubjid]
                target_rows = [r for r in target_rows if r[1] == rel.usubjid]
                if not source_rows or not target_rows:
                    continue

            src_domain, src_usubjid, src_seq = source_rows[0]
            tgt_domain, tgt_usubjid, tgt_seq = target_rows[0]

            src_seqvar = f"{src_domain}SEQ"
            tgt_seqvar = f"{tgt_domain}SEQ"

            # Source row
            records.append({
                'STUDYID': study_id,
                'RDOMAIN': src_domain,
                'USUBJID': src_usubjid,
                'IDVAR': src_seqvar,
                'IDVARVAL': str(src_seq),
                'RELTYPE': 'ONE',
                'RELID': rel.rel_id,
            })

            # Target row (reciprocal)
            records.append({
                'STUDYID': study_id,
                'RDOMAIN': tgt_domain,
                'USUBJID': tgt_usubjid,
                'IDVAR': tgt_seqvar,
                'IDVARVAL': str(tgt_seq),
                'RELTYPE': 'ONE',
                'RELID': rel.rel_id,
            })

        if not records:
            return pd.DataFrame(columns=[
                'STUDYID', 'RDOMAIN', 'USUBJID', 'IDVAR', 'IDVARVAL', 'RELTYPE', 'RELID'
            ])

        df = pd.DataFrame(records)
        return df.sort_values(['USUBJID', 'RELID', 'RDOMAIN']).reset_index(drop=True)
