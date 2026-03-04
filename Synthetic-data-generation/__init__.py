"""
SDTM Synthetic Data Generator

A protocol-driven synthetic SDTM data generator that creates clean,
SDTM-conformant clinical trial data.

Usage:
    from sdtm_synth import generate_v2

    datasets = generate_v2(
        protocol='bendita',
        output_dir='./output',
        seed=42
    )

CLI Usage:
    python -m sdtm_synth generate --protocol bendita --output ./output

Version: 2.0.0
"""

__version__ = "2.0.0"
__author__ = "Care2Data"

from .cli import generate_v2

__all__ = [
    "generate_v2",
    "__version__",
]
