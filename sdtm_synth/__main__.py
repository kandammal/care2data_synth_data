"""
Allow running the package as a module:
    python -m sdtm_synth generate --protocol bendita
"""

from .cli import main

if __name__ == '__main__':
    main()
