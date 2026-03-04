# SDTM Synthetic Data Generator v2

A protocol-driven synthetic SDTM data generator built on a canonical truth model with per-subject deterministic RNG.

## Features

- **Canonical Truth Model**: All SDTM data derived from `CanonicalSubject` objects — no cross-domain drift
- **Per-Subject RNG**: Scaling invariant — subjects 0..99 are identical whether N=100 or N=200
- **Provenance Tracking**: Every SDTM row maps back to a canonical object via `ProvenanceMap`
- **15 SDTM Domains**: DM, AE, DS, EX, CM, MH, SE, SV, VS, LB, TE, TA, TS, TV, RELREC
- **Phase 2 Realism**: AR(1) dynamics, AE perturbations on VS/LB, baseline conditioning, Weibull dropout, missingness model, dose modifications
- **Dual Conformance**: Repair layer (study days, epochs, cross-domain fixes) + tagged-category validator (structural, temporal, terminology, coherence, derived)
- **9 Protocols**: BENDITA, HS-11-421, TJ-301, PROTECT, Sutimlimab, HERALD, BDA (TYREE), USL261 (ARTEMIS), KONFIDENT
- **Reproducible**: Deterministic output with seed parameter

## Installation

```bash
pip install pandas pydantic numpy pyyaml scipy
```

## Usage

### CLI

```bash
# Generate BENDITA trial data
python -m sdtm_synth generate --protocol bendita --output ./output

# Generate with custom subject count
python -m sdtm_synth generate --protocol hs11421 --subjects 100 --seed 42

# Generate from custom spec
python -m sdtm_synth generate --spec my_trial.yaml --output ./output

# Extract trial design spec to YAML
python -m sdtm_synth extract-spec --protocol bendita --output bendita_spec.yaml

# List available protocols
python -m sdtm_synth list-protocols
```

### Python API

```python
from sdtm_synth import generate_v2
from pathlib import Path

datasets = generate_v2(
    protocol='bendita',
    output_dir=Path('./output'),
    n_subjects=100,
    seed=42,
)
```

## Architecture

### Generation Pipeline

```
Protocol Spec
     │
     ▼
┌──────────────────────────────────────────────┐
│  Per-subject (N times, independent RNG)      │
│                                              │
│  Stage 1: Timeline → consent, first_dose     │
│  Stage 2: AE candidates → accept/reject      │
│  Stage 3: Disposition → death/dropout/done   │
│  Stage 4: Censor → truncate at actual_end    │
│  Stage 5: MH, CM, EX, VS, LB                │
│           └─ realism: AR(1), perturbations   │
│                                              │
│  Output: CanonicalSubject                    │
└──────────────┬───────────────────────────────┘
               │
               ▼
┌──────────────────────────────┐
│  Materializer                │
│  Canonical → SDTM rows + SEQ│
│  Provenance tracking         │
│  RELREC from relationships   │
└──────────────┬───────────────┘
               │
     ┌─────────┼─────────┐
     ▼         ▼         ▼
   TE/TA    Conformance  v2 Validator
   TS/TV    repairs      (tagged checks)
     │         │         │
     └─────────┼─────────┘
               ▼
          CSV Export
```

### File Structure

```
sdtm_synth/
├── core/
│   ├── canonical.py          # CanonicalSubject data model
│   ├── subject_generator.py  # 7-stage per-subject pipeline
│   ├── materializer.py       # Canonical → SDTM DataFrames
│   ├── provenance.py         # Canonical ID ↔ SDTM row mapping
│   └── realism.py            # Phase 2: latent traits, AR(1), perturbations
├── spec/
│   ├── models.py             # TrialDesignSpec (Pydantic)
│   ├── extractor.py          # Protocol extraction
│   └── resolver.py           # Spec resolution + validation
├── compiler/
│   └── trial_design.py       # TE, TA, TS, TV compilation
├── conformance/
│   ├── layer.py              # Repair layer (study days, epochs, cross-domain fixes)
│   ├── v2_validator.py       # Tagged-category validation
│   └── rules.py              # Rule primitives + domain metadata
├── export/
│   └── exporter.py           # CSV export
├── terminology/
│   ├── meddra_terms.py       # Synthetic MedDRA hierarchy library
│   └── controlled_terms.py   # CDISC controlled terminology
├── utils/
│   ├── rng.py                # SubjectRNG (per-subject, record-keyed, deterministic)
│   ├── dates.py              # ISO 8601 dates, study day derivation
│   └── ids.py                # USUBJID and SEQ generation
├── tests/
│   └── test_v2_invariants.py # Scaling, call-order, RELREC stability tests
└── cli.py                    # CLI entry point + generate_v2()
```

## Key Guarantees

1. **Scaling invariance**: Subject k produces identical data regardless of total N
2. **Call-order invariance**: Domain generators produce same output regardless of execution order
3. **Provenance**: Every SDTM row traces to a canonical object
4. **RELREC stability**: Cross-domain relationships survive re-sorting
5. **Censoring**: All events bounded by [consent_date, actual_end_date]
6. **Screen failure correctness**: RFSTDTC, RFENDTC, RFPENDTC blank for screen failures

## Output

```
output/
├── dm.csv      # Demographics
├── ae.csv      # Adverse Events
├── ds.csv      # Disposition
├── ex.csv      # Exposure
├── cm.csv      # Concomitant Medications
├── mh.csv      # Medical History
├── se.csv      # Subject Elements
├── sv.csv      # Subject Visits
├── vs.csv      # Vital Signs
├── lb.csv      # Laboratory
├── te.csv      # Trial Elements
├── ta.csv      # Trial Arms
├── ts.csv      # Trial Summary
├── tv.csv      # Trial Visits
└── relrec.csv  # Related Records
```

## License

Internal use only.
