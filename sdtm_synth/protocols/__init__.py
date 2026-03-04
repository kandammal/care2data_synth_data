"""
Protocol Registry Module

Known protocol specifications and detection utilities.
"""

from .registry import (
    KNOWN_PROTOCOLS,
    get_protocol_spec,
    list_available_protocols,
    detect_protocol_from_text,
)

__all__ = [
    'KNOWN_PROTOCOLS',
    'get_protocol_spec',
    'list_available_protocols',
    'detect_protocol_from_text',
]
