# SDTM Synthetic Data Generator

A Python codebase for generating SDTM-conformant synthetic clinical trial data based on protocol specifications.

## Features

- **Protocol-Driven**: Extracts trial design from protocol documents (BENDITA, HS-11-421)
- **14 SDTM Domains**: Generates complete domain datasets:
  - Trial Design: TE, TA, TS, TV
  - Demographics: DM
  - Medical History: MH
  - Subject Elements: SE, SV, DS
  - Exposure: EX
  - Concomitant Medications: CM
  - Vital Signs: VS
  - Laboratory: LB
  - Adverse Events: AE
- **Temporal Consistency**: Enforces proper date relationships across domains
- **SDTM Conformance**: Validates against 58+ conformance rules
- **Reproducible**: Deterministic output with seed parameter

## Installation

```bash
pip install pandas pydantic numpy pyyaml
```

## Usage

### Python API

```python
from sdtm_synth.cli import generate_synthetic_data
from pathlib import Path

# Generate for BENDITA protocol (Chagas disease)
datasets = generate_synthetic_data(
    protocol='bendita',
    output_dir=Path('./output'),
    n_subjects=100,
    seed=42,
    validate=True,
    verbose=True
)

# Generate for HS-11-421 protocol (Opioid use disorder)
datasets = generate_synthetic_data(
    protocol='hs11421',
    output_dir=Path('./output_hs'),
    n_subjects=200,
    seed=42
)
```

### Custom Specifications

```python
from sdtm_synth.spec.resolver import load_spec_from_yaml

# Load custom YAML spec
spec = load_spec_from_yaml('my_trial_spec.yaml')

datasets = generate_synthetic_data(
    spec_path='my_trial_spec.yaml',
    n_subjects=50
)
```

## Supported Protocols

### BENDITA (DNDi-CH-E1224-003)
- Phase 2 Chagas disease trial
- 7 treatment arms (BZN 8/4/2 weeks, E1224 high/low, combination, placebo)
- 210 subjects (30/arm)
- 8-week treatment + 12-month follow-up

### HS-11-421
- Phase 3 opioid use disorder trial
- 2 treatment arms (SL buprenorphine vs CAM2038)
- 428 subjects
- Double-blind, double-dummy design
- 24-week treatment + 4-week follow-up

## Architecture

```
sdtm_synth/
├── spec/
│   ├── models.py       # Pydantic models for trial design
│   ├── extractor.py    # Protocol extraction logic
│   └── resolver.py     # Spec resolution (protocol/custom/hybrid)
├── compiler/
│   └── trial_design.py # TE, TA, TS, TV generators
├── backbone/
│   └── subjects.py     # DM generation and subject registry
├── timeline/
│   └── engine.py       # SE, SV, DS with temporal consistency
├── generators/
│   ├── mh.py           # Medical History
│   ├── ex.py           # Exposure
│   ├── cm.py           # Concomitant Medications
│   ├── vs.py           # Vital Signs
│   ├── lb.py           # Laboratory
│   └── ae.py           # Adverse Events
├── conformance/
│   ├── rules.py        # SDTM validation rules
│   └── layer.py        # Conformance validation layer
├── export/
│   └── exporter.py     # CSV export
├── utils/
│   ├── dates.py        # ISO 8601 date handling, study day derivation
│   ├── rng.py          # Reproducible random number generation
│   └── ids.py          # USUBJID and sequence number generation
└── cli.py              # Command-line interface
```

## Key Design Principles

1. **Single Source of Truth for Time**: DM.RFSTDTC anchors all study day (--DY) derivation
2. **Gapless Subject Elements**: SEENDTC[i] = SESTDTC[i+1] enforced
3. **Censoring**: All events bounded by [consent_date, censor_date]
4. **Deterministic**: Fixed seed ensures reproducible outputs
5. **SDTM Conformance**: ISO 8601 dates, controlled terminology, proper variable naming

## Output Format

Generated CSV files follow SDTM 3.4 conventions:
- ISO 8601 date format (YYYY-MM-DD)
- Study days derived per SDTM rules (no Day 0)
- Controlled terminology for categorical variables
- Proper domain prefixes (DM, AE, VS, etc.)

## Example Output

```
output/
├── te.csv    # Trial Elements
├── ta.csv    # Trial Arms
├── ts.csv    # Trial Summary
├── tv.csv    # Trial Visits
├── dm.csv    # Demographics
├── mh.csv    # Medical History
├── se.csv    # Subject Elements
├── sv.csv    # Subject Visits
├── ds.csv    # Disposition
├── ex.csv    # Exposure
├── cm.csv    # Concomitant Medications
├── vs.csv    # Vital Signs
├── lb.csv    # Laboratory
└── ae.csv    # Adverse Events
```

## License

Internal use only.
