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
from .conformance.layer import ConformanceLayer
from .protocols import list_available_protocols, get_protocol_spec
from .utils.rng import set_seed




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
    """Generate synthetic SDTM data via the v2 pipeline."""
    generate_v2(
        protocol=args.protocol,
        spec_path=Path(args.spec) if args.spec else None,
        output_dir=Path(args.output),
        n_subjects=args.subjects,
        seed=args.seed,
        validate=not args.no_validate,
        verbose=not args.quiet,
        batch_size=args.batch_size,
    )


def generate_v2(
    protocol: Optional[str] = None,
    spec_path: Optional[Path] = None,
    output_dir: Path = Path('./output'),
    n_subjects: Optional[int] = None,
    seed: int = 42,
    validate: bool = True,
    verbose: bool = True,
    batch_size: Optional[int] = None,
) -> Dict[str, pd.DataFrame]:
    """
    v2 Generation Pipeline — Per-subject SubjectRNG + CanonicalSubject.
    
    Scaling invariant: subjects 0..99 are identical whether N=100 or N=200.
    Call-order invariant: domain generators produce same output regardless of order.
    """
    from .core.subject_generator import generate_canonical_subject
    from .core.materializer import materialize_batched, export_datasets
    
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

    # Default batch_size to protocol's subject count (no batching unless overridden)
    if batch_size is None:
        batch_size = n

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
    
    # ── Generate + materialize in batches (streaming, O(batch_size) subject memory) ──
    stats = {'n_enrolled': 0, 'n_sf': 0, 'n_completed': 0, 'n_dead': 0, 'n_aes': 0}

    def _subject_generator(n, spec, seed, stats):
        """Yield CanonicalSubject one at a time, accumulating stats inline."""
        for idx in range(n):
            subj = generate_canonical_subject(spec, idx, seed)
            if subj.is_screen_failure:
                stats['n_sf'] += 1
            else:
                stats['n_enrolled'] += 1
            if subj.is_completed:
                stats['n_completed'] += 1
            if subj.is_dead:
                stats['n_dead'] += 1
            stats['n_aes'] += len(subj.adverse_events)
            yield subj

    if verbose:
        print(f"\nGenerating {n} subjects with per-subject RNG...")

    datasets, provenance, relationships = materialize_batched(
        _subject_generator(n, spec, seed, stats), spec, batch_size=batch_size,
    )

    if verbose:
        print(f"  Enrolled: {stats['n_enrolled']}, Screen failures: {stats['n_sf']}")
        print(f"  Completed: {stats['n_completed']}, Deaths: {stats['n_dead']}")
        print(f"  Total AEs: {stats['n_aes']}")

    if verbose:
        print(f"\nMaterializing SDTM domains...")
    
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
    
    # ── Pre-export validation (tagged categories) ──
    if validate:
        if verbose:
            print(f"\nRunning v2 conformance validator...")
        try:
            from .conformance.v2_validator import ConformanceValidator
            v2_report = ConformanceValidator().validate(datasets)
            if verbose:
                print(f"  {v2_report.summary()}")
        except Exception as e:
            if verbose:
                print(f"  v2 validator skipped: {e}")

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
        '--batch-size',
        type=int,
        default=None,
        help='Subjects per materialization batch (default: protocol subject count)'
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

