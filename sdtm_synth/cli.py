#!/usr/bin/env python3
"""
SDTM Synthetic Data Generator - Command Line Interface

Usage:
    python -m sdtm_synth generate --protocol bendita --output ./output
    python -m sdtm_synth generate --protocol hs11421 --subjects 100 --seed 42
    python -m sdtm_synth generate --protocol tj301 --output ./output
    python -m sdtm_synth generate --protocol protect --output ./output
    python -m sdtm_synth generate --spec custom_spec.yaml --output ./output
    python -m sdtm_synth extract-spec --protocol bendita --output bendita_spec.yaml
    python -m sdtm_synth list-protocols
"""

import argparse
import sys
import warnings
from pathlib import Path
from typing import Optional, Dict
import pandas as pd

from .spec.extractor import ProtocolSpecExtractor
from .spec.resolver import (
    TrialDesignSpecResolver, 
    ResolutionMode,
    save_spec_to_yaml,
    load_spec_from_yaml
)
from .compiler.trial_design import TrialDesignCompiler
from .backbone.subjects import SubjectBackboneGenerator
from .timeline.engine import TimelineEngine
from .generators.mh import MedicalHistoryGenerator
from .generators.ex import ExposureGenerator
from .generators.cm import ConcomitantMedicationsGenerator
from .generators.vs import VitalSignsGenerator
from .generators.lb import LaboratoryGenerator
from .generators.ae import AdverseEventsGenerator
from .conformance.layer import ConformanceLayer
from .export.exporter import SDTMExporter
from .protocols import list_available_protocols, get_protocol_spec
from .utils.rng import set_seed
from .utils.dates import format_iso_date, derive_study_day, parse_date
from datetime import date


def _apply_death_updates(
    datasets: Dict[str, pd.DataFrame],
    fatal_ae_subjects: Dict[str, date],
    spec
) -> Dict[str, pd.DataFrame]:
    """
    Update DM and DS domains for subjects with fatal AEs.
    
    For each subject with a fatal AE:
    - DM: Set DTHDTC (death date), DTHFL='Y'
    - DS: Add DEATH disposition record with DSLNKID linking to AE
    
    Args:
        datasets: Current datasets dict
        fatal_ae_subjects: Dict of usubjid -> death_date
        spec: Trial design specification
    
    Returns:
        Updated datasets dict
    """
    if not fatal_ae_subjects:
        return datasets
    
    dm_df = datasets.get('DM')
    ds_df = datasets.get('DS')
    ae_df = datasets.get('AE')
    
    if dm_df is None or ds_df is None:
        return datasets
    
    # Update DM for deceased subjects
    dm_df = dm_df.copy()
    if 'DTHDTC' not in dm_df.columns:
        dm_df['DTHDTC'] = ''
    if 'DTHFL' not in dm_df.columns:
        dm_df['DTHFL'] = ''
    
    for usubjid, death_date in fatal_ae_subjects.items():
        mask = dm_df['USUBJID'] == usubjid
        if mask.any():
            dm_df.loc[mask, 'DTHDTC'] = format_iso_date(death_date)
            dm_df.loc[mask, 'DTHFL'] = 'Y'
    
    datasets['DM'] = dm_df
    
    # Add DEATH records to DS
    ds_records = ds_df.to_dict('records')
    
    # Get max DSSEQ per subject
    max_seq = ds_df.groupby('USUBJID')['DSSEQ'].max().to_dict()
    
    for usubjid, death_date in fatal_ae_subjects.items():
        # Check if DEATH record already exists
        existing_death = ds_df[(ds_df['USUBJID'] == usubjid) & (ds_df['DSDECOD'] == 'DEATH')]
        if len(existing_death) > 0:
            continue
        
        # Get RFSTDTC for study day calculation
        dm_row = dm_df[dm_df['USUBJID'] == usubjid]
        rfstdtc = None
        if len(dm_row) > 0 and 'RFSTDTC' in dm_row.columns:
            rfstdtc_str = dm_row.iloc[0]['RFSTDTC']
            if rfstdtc_str:
                rfstdtc = parse_date(rfstdtc_str)
        
        # Calculate study day
        dsstdy = ''
        if rfstdtc:
            dsstdy = derive_study_day(death_date, rfstdtc)
        
        # Get AELNKID from fatal AE
        aelnkid = ''
        if ae_df is not None:
            fatal_ae = ae_df[(ae_df['USUBJID'] == usubjid) & (ae_df['AESDTH'] == 'Y')]
            if len(fatal_ae) > 0 and 'AELNKID' in fatal_ae.columns:
                aelnkid = fatal_ae.iloc[0]['AELNKID']
        
        # Create DEATH record
        dsseq = max_seq.get(usubjid, 0) + 1
        max_seq[usubjid] = dsseq
        
        death_record = {
            'STUDYID': spec.study_id,
            'DOMAIN': 'DS',
            'USUBJID': usubjid,
            'DSSEQ': dsseq,
            'DSTERM': 'DEATH',
            'DSDECOD': 'DEATH',
            'DSCAT': 'DISPOSITION EVENT',
            'DSSCAT': 'STUDY PARTICIPATION',
            'DSSTDTC': format_iso_date(death_date),
            'DSSTDY': dsstdy,
            'EPOCH': 'TREATMENT',
        }
        
        # Add DSLNKID if we have AELNKID
        if aelnkid:
            death_record['DSLNKID'] = aelnkid
        
        ds_records.append(death_record)
    
    # Recreate DS DataFrame
    ds_df = pd.DataFrame(ds_records)
    
    # Ensure column order
    base_cols = ['STUDYID', 'DOMAIN', 'USUBJID', 'DSSEQ', 'DSTERM', 'DSDECOD', 
                 'DSCAT', 'DSSCAT', 'DSSTDTC', 'DSSTDY', 'EPOCH']
    if 'DSLNKID' in ds_df.columns:
        base_cols.insert(4, 'DSLNKID')  # After DSSEQ
    
    ds_df = ds_df.sort_values(['USUBJID', 'DSSEQ']).reset_index(drop=True)
    datasets['DS'] = ds_df[[c for c in base_cols if c in ds_df.columns]]
    
    return datasets


def generate_synthetic_data(
    protocol: Optional[str] = None,
    spec_path: Optional[Path] = None,
    output_dir: Path = Path('./output'),
    n_subjects: Optional[int] = None,
    seed: int = 42,
    validate: bool = True,
    verbose: bool = True
) -> Dict[str, pd.DataFrame]:
    """
    Generate synthetic SDTM data.
    
    Args:
        protocol: Protocol name ('bendita' or 'hs11421')
        spec_path: Path to custom spec YAML file
        output_dir: Output directory for CSV files
        n_subjects: Override number of subjects
        seed: Random seed for reproducibility
        validate: Run conformance validation
        verbose: Print progress messages
        
    Returns:
        Dict of domain -> DataFrame
    """
    # Set random seed
    set_seed(seed)
    
    if verbose:
        print(f"SDTM Synthetic Data Generator")
        print(f"=" * 50)
        print(f"Seed: {seed}")
    
    # Resolve specification
    if spec_path:
        if verbose:
            print(f"Loading custom spec from: {spec_path}")
        spec = load_spec_from_yaml(spec_path)
    else:
        protocol_name = protocol or 'bendita'
        if verbose:
            print(f"Extracting spec from protocol: {protocol_name}")
        
        resolver = TrialDesignSpecResolver(
            mode=ResolutionMode.PROTOCOL,
            protocol_path=Path(f"{protocol_name}.pdf")  # Dummy path - extractor uses name
        )
        # Set protocol name for extractor to find
        resolver.protocol_path = Path(protocol_name)
        spec = resolver.resolve()
        
        assumptions = resolver.get_assumptions()
        if assumptions and verbose:
            print(f"\nAssumptions made during extraction:")
            for a in assumptions[:5]:
                print(f"  - {a.parameter}: {a.reason}")
    
    # Override subject count if specified
    if n_subjects is not None:
        # Preserve original ratios when scaling
        original_allocation = spec.demographics_defaults.subjects_per_arm
        original_total = sum(original_allocation.values()) if original_allocation else len(spec.arms)
        
        spec.demographics_defaults.total_subjects = n_subjects
        
        # Scale subjects per arm while preserving ratios
        if original_allocation and original_total > 0:
            new_allocation = {}
            allocated = 0
            arm_list = list(spec.arms)
            
            for i, arm in enumerate(arm_list):
                if arm.armcd in original_allocation:
                    ratio = original_allocation[arm.armcd] / original_total
                    if i == len(arm_list) - 1:
                        # Last arm gets remainder
                        new_allocation[arm.armcd] = n_subjects - allocated
                    else:
                        arm_n = int(round(n_subjects * ratio))
                        new_allocation[arm.armcd] = arm_n
                        allocated += arm_n
                else:
                    new_allocation[arm.armcd] = n_subjects // len(spec.arms)
            
            spec.demographics_defaults.subjects_per_arm = new_allocation
        else:
            # Equal allocation if no ratio specified
            n_arms = len(spec.arms)
            per_arm = n_subjects // n_arms
            spec.demographics_defaults.subjects_per_arm = {
                arm.armcd: per_arm for arm in spec.arms
            }
    
    if verbose:
        print(f"\nStudy: {spec.study_id}")
        print(f"Arms: {len(spec.arms)}")
        print(f"Elements: {len(spec.elements)}")
        print(f"Visits: {len(spec.visits)}")
        print(f"Total subjects: {spec.demographics_defaults.total_subjects}")
        print(f"Randomization: {spec.demographics_defaults.subjects_per_arm}")
    
    datasets = {}
    
    # 1. Compile trial design domains (TE, TA, TS, TV)
    if verbose:
        print(f"\nCompiling trial design domains...")
    
    compiler = TrialDesignCompiler(spec)
    datasets['TE'] = compiler.compile_te()
    datasets['TA'] = compiler.compile_ta()
    datasets['TS'] = compiler.compile_ts()
    datasets['TV'] = compiler.compile_tv()
    
    if verbose:
        print(f"  TE: {len(datasets['TE'])} elements")
        print(f"  TA: {len(datasets['TA'])} arm-element combinations")
        print(f"  TS: {len(datasets['TS'])} parameters")
        print(f"  TV: {len(datasets['TV'])} visits")
    
    # 2. Generate subject backbone (DM)
    if verbose:
        print(f"\nGenerating subject backbone...")
    
    backbone_gen = SubjectBackboneGenerator(spec)
    datasets['DM'], registry = backbone_gen.generate()
    
    if verbose:
        n_enrolled = len(registry.get_enrolled_subjects())
        n_screen_fail = len(registry.get_screen_failures())
        n_completers = len(registry.get_completers())
        n_dropouts = len(registry.get_dropouts())
        print(f"  DM: {len(datasets['DM'])} subjects")
        print(f"    Enrolled: {n_enrolled}")
        print(f"    Screen failures: {n_screen_fail}")
        print(f"    Completers: {n_completers}")
        print(f"    Dropouts: {n_dropouts}")
    
    # 3. Generate timeline domains (SE, SV, DS)
    if verbose:
        print(f"\nGenerating timeline domains...")
    
    timeline_engine = TimelineEngine(spec, registry)
    datasets['SE'], datasets['SV'], datasets['DS'] = timeline_engine.generate_all()
    
    if verbose:
        print(f"  SE: {len(datasets['SE'])} subject elements")
        print(f"  SV: {len(datasets['SV'])} subject visits")
        print(f"  DS: {len(datasets['DS'])} disposition records")
    
    # 4. Generate medical history (MH)
    if verbose:
        print(f"\nGenerating medical history...")
    
    mh_gen = MedicalHistoryGenerator(spec, registry)
    datasets['MH'] = mh_gen.generate()
    
    if verbose:
        print(f"  MH: {len(datasets['MH'])} conditions")
    
    # 5. Generate exposure (EX)
    if verbose:
        print(f"\nGenerating exposure...")
    
    ex_gen = ExposureGenerator(spec, registry, timeline_engine)
    datasets['EX'] = ex_gen.generate()
    
    if verbose:
        print(f"  EX: {len(datasets['EX'])} exposure records")
    
    # 6. Generate concomitant medications (CM)
    if verbose:
        print(f"\nGenerating concomitant medications...")
    
    cm_gen = ConcomitantMedicationsGenerator(spec, registry)
    datasets['CM'] = cm_gen.generate()
    
    if verbose:
        print(f"  CM: {len(datasets['CM'])} medications")
    
    # 7. Generate vital signs (VS)
    if verbose:
        print(f"\nGenerating vital signs...")
    
    vs_gen = VitalSignsGenerator(spec, registry, timeline_engine)
    datasets['VS'] = vs_gen.generate()
    
    if verbose:
        print(f"  VS: {len(datasets['VS'])} vital sign measurements")
    
    # 8. Generate laboratory (LB)
    if verbose:
        print(f"\nGenerating laboratory tests...")
    
    lb_gen = LaboratoryGenerator(spec, registry, timeline_engine)
    datasets['LB'] = lb_gen.generate()
    
    if verbose:
        print(f"  LB: {len(datasets['LB'])} lab test results")
    
    # 9. Generate adverse events (AE) with deaths enabled
    if verbose:
        print(f"\nGenerating adverse events...")
    
    ae_gen = AdverseEventsGenerator(
        spec, registry, timeline_engine,
        clean_mode=True,
        allow_deaths=True,
        death_rate=0.03  # ~3% will have fatal AEs
    )
    datasets['AE'] = ae_gen.generate()
    
    if verbose:
        print(f"  AE: {len(datasets['AE'])} adverse events")
        fatal_count = len(ae_gen.fatal_ae_subjects)
        if fatal_count > 0:
            print(f"      {fatal_count} subjects with fatal AEs")
    
    # 9b. Update DM and DS for deaths
    if ae_gen.fatal_ae_subjects:
        datasets = _apply_death_updates(datasets, ae_gen.fatal_ae_subjects, spec)
        if verbose:
            print(f"      Updated DM/DS for deaths")
    
    # 9c. Generate RELREC for cross-domain relationships
    # Per SDTM-IG Section 8.2: Relating Peer Records
    from .generators.relrec import RelatedRecordsGenerator
    relrec_gen = RelatedRecordsGenerator(spec)
    
    ae_df = datasets.get('AE')
    ds_df = datasets.get('DS')
    cm_df = datasets.get('CM')
    
    # 1. Link fatal AEs to DS DEATH records
    if ae_gen.fatal_ae_subjects and ae_df is not None and ds_df is not None:
        for usubjid in ae_gen.fatal_ae_subjects:
            fatal_ae = ae_df[(ae_df['USUBJID'] == usubjid) & (ae_df['AESDTH'] == 'Y')]
            if len(fatal_ae) > 0:
                aeseq = int(fatal_ae.iloc[0]['AESEQ'])
                death_ds = ds_df[(ds_df['USUBJID'] == usubjid) & (ds_df['DSDECOD'] == 'DEATH')]
                if len(death_ds) > 0:
                    dsseq = int(death_ds.iloc[0]['DSSEQ'])
                    relrec_gen.add_ae_ds_death_relationship(usubjid, aeseq, dsseq)
    
    # 2. Link AEs to CMs (concomitant medications treating AEs)
    # Per SDTM-IG Section 8.2.2 Example 1: AE linked to CM records
    if ae_df is not None and cm_df is not None and len(ae_df) > 0 and len(cm_df) > 0:
        # For each subject, find CMs that started on or after an AE started
        # (indicating the CM may be treating the AE)
        for usubjid in ae_df['USUBJID'].unique():
            subj_aes = ae_df[ae_df['USUBJID'] == usubjid]
            subj_cms = cm_df[cm_df['USUBJID'] == usubjid]
            
            if len(subj_cms) == 0:
                continue
            
            for _, ae_row in subj_aes.iterrows():
                ae_start = ae_row.get('AESTDTC', '')
                if not ae_start:
                    continue
                
                # Find CMs that started within 3 days after AE start (treatment window)
                related_cms = []
                for _, cm_row in subj_cms.iterrows():
                    cm_start = cm_row.get('CMSTDTC', '')
                    if not cm_start:
                        continue
                    
                    # Simple date comparison (CM starts on or after AE)
                    try:
                        ae_date = ae_start[:10]
                        cm_date = cm_start[:10]
                        if cm_date >= ae_date and cm_date <= ae_date[:8] + str(int(ae_date[8:10]) + 3).zfill(2):
                            related_cms.append(int(cm_row['CMSEQ']))
                    except (ValueError, IndexError):
                        continue
                
                # Link AE to related CMs (max 2 CMs per AE to avoid too many relationships)
                if related_cms:
                    relrec_gen.add_ae_cm_relationship(
                        usubjid=usubjid,
                        aeseq=int(ae_row['AESEQ']),
                        cmseq_list=related_cms[:2]
                    )
    
    # 3. Link AEs leading to discontinuation to DS records
    if ae_df is not None and ds_df is not None:
        # Find AEs with AEACN containing "DRUG WITHDRAWN" 
        withdrawn_aes = ae_df[ae_df['AEACN'].str.contains('WITHDRAWN', case=False, na=False)]
        for _, ae_row in withdrawn_aes.iterrows():
            usubjid = ae_row['USUBJID']
            # Find ADVERSE EVENT discontinuation record
            disc_ds = ds_df[(ds_df['USUBJID'] == usubjid) & 
                           (ds_df['DSDECOD'].str.contains('ADVERSE EVENT', case=False, na=False))]
            if len(disc_ds) > 0:
                relrec_gen.add_peer_record_relationship(
                    usubjid=usubjid,
                    records=[
                        {'rdomain': 'AE', 'idvar': 'AESEQ', 'idvarval': int(ae_row['AESEQ'])},
                        {'rdomain': 'DS', 'idvar': 'DSSEQ', 'idvarval': int(disc_ds.iloc[0]['DSSEQ'])},
                    ]
                )
    
    datasets['RELREC'] = relrec_gen.generate()
    
    if verbose and len(datasets['RELREC']) > 0:
        # Count relationship types
        relrec_df = datasets['RELREC']
        ae_ds_count = len(relrec_df[relrec_df['RDOMAIN'] == 'DS']) // 2 if 'DS' in relrec_df['RDOMAIN'].values else 0
        ae_cm_count = len(relrec_df[relrec_df['RDOMAIN'] == 'CM']) // 2 if 'CM' in relrec_df['RDOMAIN'].values else 0
        print(f"  RELREC: {len(datasets['RELREC'])} records (AE↔DS:{ae_ds_count}, AE↔CM:{ae_cm_count})")
    
    # 10. Run conformance validation
    if validate:
        if verbose:
            print(f"\nRunning conformance validation...")
        
        conformance = ConformanceLayer(strict=False)
        report = conformance.validate(datasets)
        
        if verbose:
            print(f"  {report.summary()}")
        
        # Apply fixes
        datasets = conformance.apply_fixes(datasets)
        
        # Derive missing study days
        datasets = conformance.derive_missing_study_days(datasets)
        
        # Assign epochs where missing
        datasets = conformance.assign_epochs(datasets)
        
        # Apply cross-domain repairs (DM.RFXENDTC from EX, EPOCH from SE)
        datasets = conformance.apply_cross_domain_repairs(datasets)
    
    # 11. Export to CSV
    if verbose:
        print(f"\nExporting to {output_dir}...")
    
    output_dir.mkdir(parents=True, exist_ok=True)
    exporter = SDTMExporter(output_dir)
    exported_files = exporter.export_all(datasets)
    
    if verbose:
        print(f"  Exported {len(exported_files)} domain files:")
        for f in exported_files:
            print(f"    - {f.name}")
    
    if verbose:
        print(f"\n{'=' * 50}")
        print(f"Generation complete!")
    
    return datasets


def extract_spec_command(args):
    """Extract and save trial design spec from protocol."""
    protocol_name = args.protocol.lower()
    
    # Use protocol name for extraction
    extractor = ProtocolSpecExtractor(Path(protocol_name))
    spec, assumptions = extractor.extract()
    
    # Save to YAML
    output_path = Path(args.output) if args.output else Path(f"{protocol_name}_spec.yaml")
    save_spec_to_yaml(spec, output_path)
    
    print(f"Extracted spec saved to: {output_path}")
    
    if assumptions:
        print(f"\nAssumptions made ({len(assumptions)}):")
        for a in assumptions:
            print(f"  - [{a.field}] {a.assumption}")
            if a.recommendation:
                print(f"    Recommendation: {a.recommendation}")


def list_protocols_command(args):
    """List available protocols with details."""
    print("\n" + "=" * 75)
    print("AVAILABLE PROTOCOLS")
    print("=" * 75)
    
    for proto_name in list_available_protocols():
        spec = get_protocol_spec(proto_name)
        print(f"\n{proto_name.upper()}")
        print(f"  Protocol ID: {spec['protocol_id']}")
        print(f"  Indication:  {spec['indication']}")
        print(f"  Phase:       {spec['phase']}, {spec['blinding'].replace('_', ' ').title()}")
        print(f"  Arms:        {', '.join(a['name'] for a in spec['arms'])}")
        print(f"  Subjects:    {spec['demographics']['total_subjects']}")
        print(f"  Age Range:   {spec['demographics']['age_min']}-{spec['demographics']['age_max']} years")
        print(f"  Duration:    {spec['treatment_duration_weeks']} weeks treatment")
    
    print("\n" + "=" * 75)
    print(f"Total: {len(list_available_protocols())} protocols available")
    print("\nUse: python -m sdtm_synth generate --protocol <name> --output ./output")


def generate_command(args):
    """Generate synthetic SDTM data.
    
    v2 pipeline is the single authoritative path for all generation.
    The v1 pipeline is deprecated and will be removed in a future release.
    Phase 3 corruption/imputation requires canonical truth + provenance,
    which only the v2 pipeline provides.
    """
    if getattr(args, 'v1', False):
        warnings.warn(
            "The --v1 flag is DEPRECATED. The v1 pipeline lacks canonical truth, "
            "provenance mapping, and per-subject RNG — all required for Phase 3 "
            "corruption/imputation. Use the v2 pipeline (default) instead. "
            "The --v1 flag will be removed in a future release.",
            DeprecationWarning,
            stacklevel=2,
        )
        generate_synthetic_data(
            protocol=args.protocol,
            spec_path=Path(args.spec) if args.spec else None,
            output_dir=Path(args.output),
            n_subjects=args.subjects,
            seed=args.seed,
            validate=not args.no_validate,
            verbose=not args.quiet
        )
    else:
        # v2 pipeline — single authoritative path
        generate_v2(
            protocol=args.protocol,
            spec_path=Path(args.spec) if args.spec else None,
            output_dir=Path(args.output),
            n_subjects=args.subjects,
            seed=args.seed,
            validate=not args.no_validate,
            verbose=not args.quiet
        )


def generate_v2(
    protocol: Optional[str] = None,
    spec_path: Optional[Path] = None,
    output_dir: Path = Path('./output'),
    n_subjects: Optional[int] = None,
    seed: int = 42,
    validate: bool = True,
    verbose: bool = True,
) -> Dict[str, pd.DataFrame]:
    """
    v2 Generation Pipeline — Per-subject SubjectRNG + CanonicalSubject.
    
    Scaling invariant: subjects 0..99 are identical whether N=100 or N=200.
    Call-order invariant: domain generators produce same output regardless of order.
    """
    from .core.subject_generator import generate_canonical_subject
    from .core.materializer import materialize_all, export_datasets
    
    # Set legacy seed for conformance layer compatibility
    set_seed(seed)
    
    if verbose:
        print(f"SDTM Synthetic Data Generator v2")
        print(f"=" * 50)
        print(f"Seed: {seed}")
    
    # Resolve specification (same as v1)
    if spec_path:
        spec = load_spec_from_yaml(spec_path)
    else:
        protocol_name = protocol or 'bendita'
        if verbose:
            print(f"Protocol: {protocol_name}")
        
        resolver = TrialDesignSpecResolver(
            mode=ResolutionMode.PROTOCOL,
            protocol_path=Path(f"{protocol_name}.pdf")
        )
        resolver.protocol_path = Path(protocol_name)
        spec = resolver.resolve()
    
    # Store seed in spec
    spec.study_seed = seed
    
    # Override subject count
    n = n_subjects or spec.n_subjects_default
    
    # Ensure arm_order is set
    if not spec.arm_order:
        spec.arm_order = [arm.armcd for arm in spec.arms]
    
    # Ensure subjects_per_arm is set
    if not spec.demographics.subjects_per_arm:
        n_arms = len(spec.arms)
        base = n // n_arms
        remainder = n % n_arms
        spec.demographics.subjects_per_arm = {
            arm.armcd: base + (1 if i < remainder else 0)
            for i, arm in enumerate(spec.arms)
        }
    elif n_subjects is not None:
        # Rescale existing allocation
        orig = spec.demographics.subjects_per_arm
        orig_total = sum(orig.values())
        if orig_total > 0:
            spec.demographics.subjects_per_arm = {
                armcd: max(1, int(round(n * cnt / orig_total)))
                for armcd, cnt in orig.items()
            }
    
    if verbose:
        print(f"Study: {spec.study_id}")
        print(f"Arms: {spec.get_arm_order_list()}")
        print(f"Subjects: {n}")
        print(f"Allocation: {spec.demographics.subjects_per_arm}")
    
    # ── Generate all subjects (per-subject RNG, scaling invariant) ──
    if verbose:
        print(f"\nGenerating {n} subjects with per-subject RNG...")
    
    canonical_subjects = []
    for idx in range(n):
        subj = generate_canonical_subject(spec, idx, seed)
        canonical_subjects.append(subj)
    
    if verbose:
        n_enrolled = sum(1 for s in canonical_subjects if not s.is_screen_failure)
        n_sf = sum(1 for s in canonical_subjects if s.is_screen_failure)
        n_completed = sum(1 for s in canonical_subjects if s.is_completed)
        n_dead = sum(1 for s in canonical_subjects if s.is_dead)
        n_aes = sum(len(s.adverse_events) for s in canonical_subjects)
        print(f"  Enrolled: {n_enrolled}, Screen failures: {n_sf}")
        print(f"  Completed: {n_completed}, Deaths: {n_dead}")
        print(f"  Total AEs: {n_aes}")
    
    # ── Materialize SDTM ──
    if verbose:
        print(f"\nMaterializing SDTM domains...")
    
    datasets, provenance, relationships = materialize_all(canonical_subjects, spec)
    
    if verbose:
        for domain, df in sorted(datasets.items()):
            if df is not None and len(df) > 0:
                print(f"  {domain}: {len(df)} records")
    
    # ── Trial Design Domains (TE, TA, TS, TV) ── keep from v1
    try:
        compiler = TrialDesignCompiler(spec)
        datasets['TE'] = compiler.compile_te()
        datasets['TA'] = compiler.compile_ta()
        datasets['TS'] = compiler.compile_ts()
        datasets['TV'] = compiler.compile_tv()
        if verbose:
            print(f"  TE: {len(datasets['TE'])}, TA: {len(datasets['TA'])}, TS: {len(datasets['TS'])}, TV: {len(datasets['TV'])}")
    except Exception as e:
        if verbose:
            print(f"  Trial design domains skipped: {e}")
    
    # ── LB/VS via canonical truth (Phase 2) ──
    # VS/LB are now generated as part of the 7-stage subject pipeline
    # and materialized from CanonicalSubject.vs_records / lb_records.
    # No legacy generator fallback needed.
    if verbose:
        vs_count = len(datasets.get('VS', []))
        lb_count = len(datasets.get('LB', []))
        print(f"  VS (v2 canonical): {vs_count}, LB (v2 canonical): {lb_count}")
    
    # ── Conformance ──
    if validate:
        if verbose:
            print(f"\nRunning conformance validation...")
        
        try:
            conformance = ConformanceLayer(strict=False)
            report = conformance.validate(datasets)
            if verbose:
                print(f"  {report.summary()}")
            
            datasets = conformance.apply_fixes(datasets)
            datasets = conformance.derive_missing_study_days(datasets)
            datasets = conformance.assign_epochs(datasets)
            datasets = conformance.apply_cross_domain_repairs(datasets)
        except Exception as e:
            if verbose:
                print(f"  Conformance skipped: {e}")
    
    # ── Export ──
    if verbose:
        print(f"\nExporting to {output_dir}...")
    
    output_dir.mkdir(parents=True, exist_ok=True)
    export_datasets(datasets, str(output_dir))
    
    if verbose:
        print(f"\n{'=' * 50}")
        print(f"v2 Generation complete!")
        print(f"  Provenance: {len(provenance._canonical_to_sdtm)} canonical objects tracked")
        print(f"  Relationships: {len(relationships)} cross-domain links")
    
    return datasets


def main():
    """Main entry point for CLI."""
    parser = argparse.ArgumentParser(
        description='SDTM Synthetic Data Generator',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  Generate BENDITA trial data:
    python -m sdtm_synth generate --protocol bendita --output ./output
    
  Generate HS-11-421 trial data with custom subject count:
    python -m sdtm_synth generate --protocol hs11421 --subjects 100 --seed 42
    
  Generate from custom spec file:
    python -m sdtm_synth generate --spec my_trial.yaml --output ./output
    
  Extract trial design spec to YAML:
    python -m sdtm_synth extract-spec --protocol bendita --output bendita_spec.yaml
        """
    )
    
    subparsers = parser.add_subparsers(dest='command', help='Commands')
    
    # Generate command
    gen_parser = subparsers.add_parser('generate', help='Generate synthetic SDTM data')
    gen_parser.add_argument(
        '--protocol', '-p',
        choices=list_available_protocols(),
        help='Protocol to use (use list-protocols to see available)'
    )
    gen_parser.add_argument(
        '--spec', '-s',
        help='Path to custom spec YAML file'
    )
    gen_parser.add_argument(
        '--output', '-o',
        default='./output',
        help='Output directory (default: ./output)'
    )
    gen_parser.add_argument(
        '--subjects', '-n',
        type=int,
        help='Override number of subjects'
    )
    gen_parser.add_argument(
        '--seed',
        type=int,
        default=42,
        help='Random seed (default: 42)'
    )
    gen_parser.add_argument(
        '--no-validate',
        action='store_true',
        help='Skip conformance validation'
    )
    gen_parser.add_argument(
        '--quiet', '-q',
        action='store_true',
        help='Suppress progress messages'
    )
    gen_parser.add_argument(
        '--v1',
        action='store_true',
        help='DEPRECATED: Use v1 generation pipeline (lacks canonical truth + provenance, will be removed)'
    )
    gen_parser.set_defaults(func=generate_command)
    
    # Extract-spec command
    extract_parser = subparsers.add_parser('extract-spec', help='Extract trial design spec from protocol')
    extract_parser.add_argument(
        '--protocol', '-p',
        required=True,
        choices=list_available_protocols(),
        help='Protocol to extract'
    )
    extract_parser.add_argument(
        '--output', '-o',
        help='Output YAML file (default: {protocol}_spec.yaml)'
    )
    extract_parser.set_defaults(func=extract_spec_command)
    
    # List-protocols command
    list_parser = subparsers.add_parser('list-protocols', help='List available protocols')
    list_parser.set_defaults(func=list_protocols_command)
    
    # Parse arguments
    args = parser.parse_args()
    
    if args.command is None:
        parser.print_help()
        sys.exit(1)
    
    # Run command
    args.func(args)




if __name__ == "__main__":
    main()

