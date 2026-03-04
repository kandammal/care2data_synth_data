"""
SDTM Synthetic Data Generator

A protocol-driven synthetic SDTM data generator that creates clean,
SDTM-conformant clinical trial data.

Usage:
    from sdtm_synth import generate_synthetic_data
    
    datasets = generate_synthetic_data(
        protocol='bendita',
        output_dir='./output',
        seed=42
    )

CLI Usage:
    python -m sdtm_synth generate --protocol bendita --output ./output

Version: 1.0.0
"""

__version__ = "1.0.0"
__author__ = "Claude"

from .cli import generate_synthetic_data

__all__ = [
    "generate_synthetic_data",
    "__version__",
]
