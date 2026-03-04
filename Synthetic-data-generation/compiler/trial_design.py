"""
SDTM Synthetic Data Generator - Trial Design Compiler

This module compiles the trial design specification into SDTM trial design datasets:
- TE (Trial Elements)
- TA (Trial Arms)
- TS (Trial Summary)
- TV (Trial Visits)
"""

from __future__ import annotations
from typing import List, Dict, Any, Optional
import pandas as pd

from ..spec.models import TrialDesignSpec, ElementSpec, ArmPath, ArmPathItem, VisitSpec, ArmSpec
from ..terminology.controlled_terminology import TSPARMCD_TO_TSPARM


class TrialDesignCompiler:
    """
    Compiles trial design specification into SDTM trial design datasets.
    
    Generates:
    - TE: Trial Elements
    - TA: Trial Arms
    - TS: Trial Summary
    - TV: Trial Visits
    """
    
    def __init__(self, spec: TrialDesignSpec):
        """
        Initialize the compiler.
        
        Args:
            spec: Validated trial design specification
        """
        self.spec = spec
        self._element_lookup: Dict[str, ElementSpec] = {
            elem.etcd: elem for elem in spec.elements
        }
    
    def compile_all(self) -> Dict[str, pd.DataFrame]:
        """
        Compile all trial design datasets.
        
        Returns:
            Dict mapping domain name to DataFrame
        """
        return {
            'TE': self.compile_te(),
            'TA': self.compile_ta(),
            'TS': self.compile_ts(),
            'TV': self.compile_tv(),
        }
    
    def compile_te(self) -> pd.DataFrame:
        """
        Compile Trial Elements (TE) dataset.
        
        Structure: One record per element.
        """
        records = []
        
        for elem in self.spec.elements:
            record = {
                'STUDYID': self.spec.study_id,
                'DOMAIN': 'TE',
                'ETCD': elem.etcd,
                'ELEMENT': elem.element,
                'TESTRL': elem.start_rule,
                'TEENRL': elem.end_rule,
            }
            
            # Add optional TEDUR if duration is specified
            if elem.nominal_duration_days is not None:
                record['TEDUR'] = f"P{elem.nominal_duration_days}D"
            
            records.append(record)
        
        df = pd.DataFrame(records)
        
        # Ensure column order
        cols = ['STUDYID', 'DOMAIN', 'ETCD', 'ELEMENT', 'TESTRL', 'TEENRL']
        if 'TEDUR' in df.columns:
            cols.append('TEDUR')
        
        return df[cols]
    
    def compile_ta(self) -> pd.DataFrame:
        """
        Compile Trial Arms (TA) dataset.
        
        Structure: One record per planned element per arm.
        For crossover designs, each sequence (AB, BA, etc.) is treated as an arm.
        TAESSION identifies each unique session within an arm (typically 1 for single-session trials).
        """
        records = []
        
        # Crossover: generate TA from crossover sequences
        if self.spec.is_crossover and self.spec.crossover_sequences:
            for seq_def in self.spec.crossover_sequences:
                seqcd = seq_def['seqcd'] if isinstance(seq_def, dict) else seq_def.seqcd
                label = seq_def.get('label', seqcd) if isinstance(seq_def, dict) else getattr(seq_def, 'label', seqcd)
                periods = seq_def['periods'] if isinstance(seq_def, dict) else seq_def.periods
                
                etord = 0
                prev_end = 0
                for p in periods:
                    p_period = p['period'] if isinstance(p, dict) else p.period
                    p_armcd = p['armcd'] if isinstance(p, dict) else p.armcd
                    p_start = p['start_day'] if isinstance(p, dict) else p.start_day
                    p_end = p['end_day'] if isinstance(p, dict) else p.end_day
                    p_washout = p.get('washout_days_before', 0) if isinstance(p, dict) else getattr(p, 'washout_days_before', 0)
                    p_epoch = p.get('epoch', f'PERIOD {p_period}') if isinstance(p, dict) else getattr(p, 'epoch', f'PERIOD {p_period}')
                    
                    # Add washout element if applicable
                    if p_washout > 0 and prev_end > 0:
                        etord += 1
                        records.append({
                            'STUDYID': self.spec.study_id,
                            'DOMAIN': 'TA',
                            'ARMCD': seqcd,
                            'ARM': label,
                            'TAETORD': etord,
                            'ETCD': f'WASHOUT',
                            'ELEMENT': f'Washout {p_period - 1}',
                            'TABRANCH': '',
                            'TATRANS': '',
                            'EPOCH': f'WASHOUT {p_period - 1}',
                        })
                    
                    # Add treatment period element
                    etord += 1
                    arm_spec = self.spec.get_arm_by_armcd(p_armcd)
                    element_name = arm_spec.arm if arm_spec else p_armcd
                    records.append({
                        'STUDYID': self.spec.study_id,
                        'DOMAIN': 'TA',
                        'ARMCD': seqcd,
                        'ARM': label,
                        'TAETORD': etord,
                        'ETCD': f'TRT_P{p_period}',
                        'ELEMENT': f'Treatment Period {p_period} ({element_name})',
                        'TABRANCH': '',
                        'TATRANS': '',
                        'EPOCH': p_epoch,
                    })
                    prev_end = p_end
        else:
            # Parallel: use arm paths
            for arm in self.spec.arms:
                arm_path = self.spec.get_arm_path(arm.armcd)
                if arm_path is None:
                    continue
                
                element_items = sorted(arm_path.elements, key=lambda x: x.taetord)
                
                for i, item in enumerate(element_items):
                    elem = self._element_lookup.get(item.etcd)
                    if elem is None:
                        raise ValueError(f"Element {item.etcd} in arm {arm.armcd} not found in elements")
                    
                    record = {
                        'STUDYID': self.spec.study_id,
                        'DOMAIN': 'TA',
                        'ARMCD': arm.armcd,
                        'ARM': arm.arm,
                        'TAETORD': item.taetord,
                        'ETCD': item.etcd,
                        'ELEMENT': elem.element,
                        'TABRANCH': '',
                        'TATRANS': '',
                        'EPOCH': elem.epoch,
                    }
                    
                    if i < len(element_items) - 1:
                        next_item = element_items[i + 1]
                        next_elem = self._element_lookup.get(next_item.etcd)
                        if next_elem:
                            record['TATRANS'] = f"Transition to {next_elem.element}"
                    
                    records.append(record)
        
        df = pd.DataFrame(records)
        
        # Add TAESSION - for single-session trials, all records have TAESSION=1
        # Each unique arm/taetord combination within a session
        df['TAESSION'] = 1
        
        # Ensure column order per SDTM-IG
        cols = ['STUDYID', 'DOMAIN', 'ARMCD', 'ARM', 'TAETORD', 'ETCD', 'ELEMENT', 
                'TABRANCH', 'TATRANS', 'EPOCH', 'TAESSION']
        
        # Sort by ARMCD, TAETORD
        df = df.sort_values(['ARMCD', 'TAETORD']).reset_index(drop=True)
        
        return df[[c for c in cols if c in df.columns]]
    
    def compile_ts(self) -> pd.DataFrame:
        """
        Compile Trial Summary (TS) dataset.
        
        Structure: One record per trial summary parameter.
        Uses standard CDISC SDTM Trial Summary parameter codes.
        Format matches CDISC TS domain structure with all required columns.
        """
        records = []
        global_seq = [0]  # Mutable counter for global TSSEQ
        params_added = set()  # Track which parameter codes have been added
        
        # Build lookup of spec-defined parameters
        spec_params = {}
        if self.spec.ts_parameters:
            for p in self.spec.ts_parameters:
                spec_params[p.tsparmcd] = p.tsval
        
        def get_spec_value(tsparmcd: str, default: str) -> str:
            """Get value from spec if defined, otherwise use default."""
            return spec_params.get(tsparmcd, default)
        
        def add_param(tsparmcd: str, tsval: str, 
                     tsgrpid: str = '', tsvalnf: str = '', 
                     tsvalcd: str = '', tsvcdref: str = '', tsvcdver: str = ''):
            """Helper to add a TS parameter record.
            
            SD1070 FIX: TSPARM is looked up from canonical TSPARMCD_TO_TSPARM mapping.
            Never pass TSPARM as a parameter - it's always derived from TSPARMCD.
            """
            if not tsval and not tsvalnf:
                return
            
            # SD1070 FIX: Always look up TSPARM from canonical mapping
            tsparm = TSPARMCD_TO_TSPARM.get(tsparmcd, tsparmcd)
            
            # Global TSSEQ: unique across all TS records (Contract 8)
            global_seq[0] += 1
            params_added.add(tsparmcd)
            
            records.append({
                'STUDYID': self.spec.study_id,
                'DOMAIN': 'TS',
                'TSSEQ': global_seq[0],
                'TSGRPID': tsgrpid,
                'TSPARMCD': tsparmcd,
                'TSPARM': tsparm,  # Always from canonical lookup
                'TSVAL': tsval,
                'TSVALNF': tsvalnf,
                'TSVALCD': tsvalcd,
                'TSVCDREF': tsvcdref,
                'TSVCDVER': tsvcdver,
            })
        
        # Get study dates
        study_start = self.spec.time_conventions.study_start_date_default
        study_start_str = study_start.isoformat() if study_start else ''
        
        # Calculate trial length
        total_days = sum(e.nominal_duration_days for e in self.spec.elements)
        
        # Core study parameters
        add_param('STUDYID', self.spec.study_id)
        add_param('TITLE', self.spec.title or self.spec.study_id)
        
        # Trial phase with CDISC CT coding
        phase_map = {
            '1': ('PHASE I TRIAL', 'C15600'),
            '2': ('PHASE II TRIAL', 'C15601'),
            '3': ('PHASE III TRIAL', 'C15602'),
            '4': ('PHASE IV TRIAL', 'C49686'),
        }
        phase_val, phase_code = phase_map.get(self.spec.phase, ('', ''))
        if phase_val:
            add_param('TPHASE', phase_val, 
                     tsvalcd=phase_code, tsvcdref='CDISC CT CDISC', tsvcdver='2023-12-15')
        
        # Study type
        add_param('STYPE', 'INTERVENTIONAL', 
                 tsvalcd='C98388', tsvcdref='CDISC CT CDISC', tsvcdver='2023-12-15')
        
        # Trial design parameters - use spec values if defined
        tblind = get_spec_value('TBLIND', 'DOUBLE BLIND')
        tblind_codes = {
            'DOUBLE BLIND': ('C15228', 'CDISC CT CDISC'),
            'SINGLE BLIND': ('C15227', 'CDISC CT CDISC'),
            'OPEN LABEL': ('C49659', 'CDISC CT CDISC'),
        }
        tblind_cd, tblind_ref = tblind_codes.get(tblind, ('', ''))
        add_param('TBLIND', tblind,
                 tsvalcd=tblind_cd, tsvcdref=tblind_ref, tsvcdver='2023-12-15' if tblind_cd else '')
        
        # Control type - only add if study has placebo arm
        has_placebo = any('PLACEBO' in arm.arm.upper() or arm.armcd == 'PBO' for arm in self.spec.arms)
        if has_placebo:
            add_param('TCNTRL', 'PLACEBO',
                     tsvalcd='C49648', tsvcdref='CDISC CT CDISC', tsvcdver='2023-12-15')
        else:
            tcntrl = get_spec_value('TCNTRL', '')
            if tcntrl:
                add_param('TCNTRL', tcntrl)
        
        add_param('TINDTP', 'TREATMENT',
                 tsvalcd='C49656', tsvcdref='CDISC CT CDISC', tsvcdver='2023-12-15')
        
        # Intervention model - use spec value if defined
        intmodel = get_spec_value('SDESIGN', 'PARALLEL')
        intmodel_codes = {
            'PARALLEL': ('C82639', 'CDISC CT CDISC'),
            'CROSSOVER': ('C82638', 'CDISC CT CDISC'),
            'SINGLE GROUP': ('C82641', 'CDISC CT CDISC'),
            'FACTORIAL': ('C82640', 'CDISC CT CDISC'),
        }
        intmodel_cd, intmodel_ref = intmodel_codes.get(intmodel, ('', ''))
        add_param('INTMODEL', intmodel,
                 tsvalcd=intmodel_cd, tsvcdref=intmodel_ref, tsvcdver='2023-12-15' if intmodel_cd else '')
        add_param('SDESIGN', intmodel,
                 tsvalcd=intmodel_cd, tsvcdref=intmodel_ref, tsvcdver='2023-12-15' if intmodel_cd else '')
        
        add_param('INTTYPE', 'DRUG',
                 tsvalcd='C1909', tsvcdref='CDISC CT CDISC', tsvcdver='2023-12-15')
        
        # Randomization - use spec value if defined
        random_val = get_spec_value('RANDOM', 'Y')
        random_code = 'C49488' if random_val == 'Y' else 'C49487'
        add_param('RANDOM', random_val,
                 tsvalcd=random_code, tsvcdref='CDISC CT CDISC', tsvcdver='2023-12-15')
        
        add_param('ADDON', 'N',
                 tsvalcd='C49487', tsvcdref='CDISC CT CDISC', tsvcdver='2023-12-15')
        add_param('ADAPT', 'N',
                 tsvalcd='C49487', tsvcdref='CDISC CT CDISC', tsvcdver='2023-12-15')
        
        # Subject parameters
        add_param('PLANSUB', str(self.spec.demographics.total_subjects))
        add_param('ACTSUB', str(self.spec.demographics.total_subjects))
        add_param('NARMS', str(len(self.spec.arms)))
        add_param('HLTSUBJI', 'N',
                 tsvalcd='C49487', tsvcdref='CDISC CT CDISC', tsvcdver='2023-12-15')
        
        # Age parameters
        age_min = self.spec.demographics.age_min
        age_max = self.spec.demographics.age_max
        add_param('AGEMIN', f'P{age_min}Y')
        if age_max and age_max < 999:
            add_param('AGEMAX', f'P{age_max}Y')
        else:
            add_param('AGEMAX', '', tsvalnf='PINF')
        
        # Sex of participants
        add_param('SEXPOP', 'BOTH',
                 tsvalcd='C49636', tsvcdref='CDISC CT CDISC', tsvcdver='2023-12-15')
        
        # Trial duration
        if total_days > 0:
            if total_days >= 365:
                months = total_days // 30
                add_param('LENGTH', f'P{months}M')
            elif total_days >= 30:
                weeks = total_days // 7
                add_param('LENGTH', f'P{weeks}W')
            else:
                add_param('LENGTH', f'P{total_days}D')
        
        # Dates
        add_param('SSTDTC', study_start_str)
        
        # Therapeutic area and indication
        if self.spec.therapeutic_area:
            add_param('TDIGRP', self.spec.therapeutic_area)
        
        # Add indication from spec if defined
        indic = get_spec_value('INDIC', '')
        if indic:
            add_param('INDIC', indic)
        
        # Investigational treatment(s)
        treatments = set()
        for arm in self.spec.arms:
            for regimen in arm.regimen:
                if regimen.extrt and regimen.extrt.upper() != 'PLACEBO':
                    treatments.add(regimen.extrt)
        for trt in sorted(treatments):
            add_param('TRT', trt)
        
        # Add custom parameters from spec
        for param in self.spec.ts_parameters:
            # Skip if already added via standard params
            if param.tsparmcd in params_added:
                continue
            add_param(param.tsparmcd, param.tsval)
        
        # =================================================================
        # P21 Required/Expected Parameters - Add defaults if not in spec
        # =================================================================
        
        # Sponsor info
        if 'SPONSOR' not in params_added:
            add_param('SPONSOR', 
                     get_spec_value('SPONSOR', 'PHARMACEUTICAL COMPANY'))
        
        # Primary objective
        if 'OBJPRIM' not in params_added:
            add_param('OBJPRIM', 
                     get_spec_value('OBJPRIM', 'To evaluate the efficacy and safety of the investigational treatment'))
        
        # Secondary objective
        if 'OBJSEC' not in params_added:
            add_param('OBJSEC',
                     get_spec_value('OBJSEC', 'To evaluate pharmacokinetics and immunogenicity'))
        
        # Primary outcome measure
        if 'OUTMSPRI' not in params_added:
            add_param('OUTMSPRI',
                     get_spec_value('OUTMSPRI', 'Change from baseline in primary endpoint'))
        
        # Trial type - EFFICACY A is correct TTYPE value per CDISC CT
        if 'TTYPE' not in params_added:
            add_param('TTYPE', 'EFFICACY A',
                     tsvalcd='C49666', tsvcdref='CDISC CT CDISC', tsvcdver='2023-12-15')
        
        # Pharmacologic class
        if 'PCLAS' not in params_added:
            add_param('PCLAS',
                     get_spec_value('PCLAS', 'MONOCLONAL ANTIBODY'),
                     tsvcdref='MED-RT')  # Use MED-RT per CDISC CT DICTNAM
        
        # Therapeutic area
        if 'THERAREA' not in params_added:
            tarea = self.spec.therapeutic_area or 'IMMUNOLOGY'
            add_param('THERAREA', tarea)
        
        # Stopping rule
        if 'STOPRULE' not in params_added:
            add_param('STOPRULE',
                     get_spec_value('STOPRULE', 'Study may be stopped for safety concerns per DMC recommendation'))
        
        # Country of first site
        if 'FCNTRY' not in params_added:
            fcntry = 'USA'
            if hasattr(self.spec, 'demographics') and self.spec.demographics:
                if hasattr(self.spec.demographics, 'defaults') and self.spec.demographics.defaults:
                    fcntry = self.spec.demographics.defaults.country or 'USA'
            add_param('FCNTRY',
                     get_spec_value('FCNTRY', fcntry))
        
        # Regulatory ID
        if 'REGID' not in params_added:
            add_param('REGID',
                     get_spec_value('REGID', 'NCT00000000'))
        
        # Number of cohorts
        if 'NCOHORT' not in params_added:
            add_param('NCOHORT',
                     get_spec_value('NCOHORT', str(len(self.spec.arms))))
        
        # Data cutoff date
        if 'DCUTDTC' not in params_added:
            add_param('DCUTDTC', 
                     get_spec_value('DCUTDTC', ''))
        
        # Data cutoff description
        if 'DCUTDESC' not in params_added:
            add_param('DCUTDESC',
                     get_spec_value('DCUTDESC', 'Final database lock'))
        
        # Study end date
        if 'SENDTC' not in params_added:
            add_param('SENDTC',
                     get_spec_value('SENDTC', ''))
        
        # Indicator parameters (Y/N flags)
        indicator_params = [
            ('EXTTIND', 'N'),
            ('PDPSTIND', 'N'),
            ('PDSTIND', 'N'),
            ('PIPIND', 'N'),
            ('RDIND', 'N'),
            ('ONGOSIND', 'N'),
        ]
        for parmcd, default in indicator_params:
            if parmcd not in params_added:
                val = get_spec_value(parmcd, default)
                code = 'C49488' if val == 'Y' else 'C49487'
                add_param(parmcd, val,
                         tsvalcd=code, tsvcdref='CDISC CT CDISC', tsvcdver='2023-12-15')
        
        # SDTM versions - these should have proper values, not NA
        if 'SDTIGVER' not in params_added:
            add_param('SDTIGVER', '3.4')
        if 'SDTMVER' not in params_added:
            add_param('SDTMVER', '2.0')
        
        df = pd.DataFrame(records)
        
        # Ensure column order matches sample
        cols = ['STUDYID', 'DOMAIN', 'TSSEQ', 'TSGRPID', 'TSPARMCD', 'TSPARM', 
                'TSVAL', 'TSVALNF', 'TSVALCD', 'TSVCDREF', 'TSVCDVER']
        
        return df[cols]
    
    def compile_tv(self) -> pd.DataFrame:
        """
        Compile Trial Visits (TV) dataset.
        
        Structure: One record per planned visit.
        Includes window bounds and collection flags as supplemental columns.
        """
        records = []
        
        for visit in self.spec.visits:
            record = {
                'STUDYID': self.spec.study_id,
                'DOMAIN': 'TV',
                'VISITNUM': visit.visitnum,
                'VISIT': visit.visit,
                'VISITDY': visit.nominal_day,
                'TVSTRL': visit.tvstrl or f"Study Day {visit.nominal_day}",
                # TVENRL - End Rule for visit (expected per SDTM-IG)
                'TVENRL': visit.tvenrl or f"End of {visit.visit}",
                # Window bounds (for validation and SV logic)
                'TVWNDWLO': visit.window_lower if visit.window_lower else 0,
                'TVWNDWHI': visit.window_upper if visit.window_upper else 0,
            }
            
            if visit.epoch:
                record['EPOCH'] = visit.epoch
            
            # Collection flags (useful for validating what data should exist at each visit)
            flags = visit.collection_flags
            record['TVCOLVS'] = 'Y' if flags.vs else 'N'
            record['TVCOLLB'] = 'Y' if flags.lb else 'N'
            record['TVCOLEX'] = 'Y' if flags.ex else 'N'
            record['TVCOLAE'] = 'Y' if flags.ae else 'N'
            record['TVCOLCM'] = 'Y' if flags.cm else 'N'
            
            records.append(record)
        
        df = pd.DataFrame(records)
        
        # Sort by VISITNUM
        df = df.sort_values('VISITNUM').reset_index(drop=True)
        
        cols = ['STUDYID', 'DOMAIN', 'VISITNUM', 'VISIT', 'VISITDY', 
                'TVWNDWLO', 'TVWNDWHI', 'TVSTRL', 'TVENRL', 'EPOCH',
                'TVCOLVS', 'TVCOLLB', 'TVCOLEX', 'TVCOLAE', 'TVCOLCM']
        
        return df[[c for c in cols if c in df.columns]]
    
    def _get_ts_parm_label(self, tsparmcd: str) -> str:
        """Get human-readable label for TS parameter code."""
        labels = {
            'STUDYID': 'Study Identifier',
            'SSTDTC': 'Study Start Date',
            'SENDTC': 'Study End Date',
            'TITLE': 'Trial Title',
            'STYPE': 'Study Type',
            'TPHASE': 'Trial Phase Classification',
            'TTYPE': 'Trial Type',
            'TBLIND': 'Trial Blinding Schema',
            'TCNTRL': 'Control Type',
            'TINDTP': 'Trial Intent Type',
            'THERAREA': 'Therapeutic Area',
            'TDIGRP': 'Diagnosis Group',
            'RANDOM': 'Trial is Randomized',
            'NARMS': 'Planned Number of Arms',
            'PCNT': 'Planned Number of Subjects',
            'PLANSUB': 'Planned Number of Subjects',
            'ACTSUB': 'Actual Number of Subjects',
            'LENGTH': 'Trial Length',
            'INDIC': 'Trial Disease/Condition Indication',
            'STOTEFRT': 'Study Territory',
            'SPONSOR': 'Clinical Study Sponsor',
            'REGID': 'Registry Identifier',
            'ADDON': 'Added on to Existing Treatments',
            'ADAPT': 'Adaptive Design',
            'AGEMIN': 'Planned Minimum Age of Subjects',
            'AGEMAX': 'Planned Maximum Age of Subjects',
            'SEXPOP': 'Sex of Participants',
            'INTMODEL': 'Intervention Model',
            'INTTYPE': 'Intervention Type',
            'HLTSUBJI': 'Healthy Subject Indicator',
            'TRT': 'Investigational Therapy or Treatment',
            'CURTRT': 'Current Therapy or Treatment',
            'OBJPRIM': 'Trial Primary Objective',
            'OBJSEC': 'Trial Secondary Objective',
            'OUTMSPRI': 'Primary Outcome Measure',
            'OUTMSSEC': 'Secondary Outcome Measure',
            'FCNTRY': 'Planned Country of Investigational Sites',
            'DCUTDTC': 'Data Cutoff Date',
            'DCUTDESC': 'Data Cutoff Description',
            'STOPRULE': 'Study Stop Rules',
            'STRATFCT': 'Stratification Factor',
            'RANDQT': 'Randomization Quotient',
            'PCLAS': 'Pharmacologic Class',
            'SDTIGVER': 'SDTM IG Version',
            'SDTMVER': 'SDTM Version',
            'THERAREA': 'Therapeutic Area',
        }
        
        return labels.get(tsparmcd, tsparmcd)
    
    def get_visit_by_number(self, visitnum: int) -> Optional[VisitSpec]:
        """Get visit specification by visit number."""
        for visit in self.spec.visits:
            if visit.visitnum == visitnum:
                return visit
        return None
    
    def get_visits_for_epoch(self, epoch: str) -> List[VisitSpec]:
        """Get all visits for a given epoch."""
        return [v for v in self.spec.visits if v.epoch == epoch]
    
    def get_element_sequence_for_arm(self, armcd: str) -> List[ElementSpec]:
        """Get ordered list of elements for an arm."""
        arm_path = self.spec.get_arm_path(armcd)
        if arm_path is None:
            return []
        
        elements = []
        element_items = sorted(arm_path.elements, key=lambda x: x.taetord)
        for item in element_items:
            elem = self._element_lookup.get(item.etcd)
            if elem:
                elements.append(elem)
        return elements
