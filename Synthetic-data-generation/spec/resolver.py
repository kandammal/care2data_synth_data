"""
Spec Resolver - Resolves trial design specifications from multiple sources.

Supports three modes:
- protocol: Use only protocol-extracted spec
- custom: Use only user-provided YAML/JSON override
- hybrid: Protocol spec + user overrides (user wins on conflicts)
"""

from enum import Enum
from pathlib import Path
from typing import Any, List, Optional, Union
import json
import math
import warnings
import yaml

from .models import TrialDesignSpec
from .extractor import ProtocolSpecExtractor


# ─── SciPy availability (for Beta CDF) ──────────────────────────────────────
try:
    from scipy.stats import beta as beta_dist
    HAS_SCIPY = True
except ImportError:
    HAS_SCIPY = False


class ResolutionMode(str, Enum):
    """Mode for resolving trial design specifications."""
    PROTOCOL = "protocol"
    CUSTOM = "custom"
    HYBRID = "hybrid"


class TrialDesignSpecResolver:
    """
    Resolves trial design specifications from protocol extraction and/or user overrides.
    """
    
    def __init__(
        self,
        mode: ResolutionMode = ResolutionMode.PROTOCOL,
        protocol_path: Optional[Path] = None,
        override_path: Optional[Path] = None,
        override_dict: Optional[dict] = None
    ):
        """
        Initialize the resolver.
        
        Args:
            mode: Resolution mode (protocol, custom, or hybrid)
            protocol_path: Path to protocol PDF for extraction
            override_path: Path to YAML/JSON file with overrides
            override_dict: Direct dict with overrides (alternative to file)
        """
        self.mode = mode
        self.protocol_path = protocol_path
        self.override_path = override_path
        self.override_dict = override_dict
        self.assumptions: list = []
    
    def resolve(self) -> TrialDesignSpec:
        """
        Resolve the trial design specification based on configured mode.
        
        Returns:
            TrialDesignSpec: The resolved specification with precomputed P_exp cache.
        """
        if self.mode == ResolutionMode.PROTOCOL:
            spec = self._resolve_from_protocol()
        elif self.mode == ResolutionMode.CUSTOM:
            spec = self._resolve_from_custom()
        elif self.mode == ResolutionMode.HYBRID:
            spec = self._resolve_hybrid()
        else:
            raise ValueError(f"Unknown resolution mode: {self.mode}")
        
        # Contract 4: precompute and cache P_exp + pool_size at resolution time
        _finalize_spec(spec)
        return spec
    
    def _resolve_from_protocol(self) -> TrialDesignSpec:
        """Extract spec purely from protocol."""
        # Handle both Path and string inputs
        if self.protocol_path is None:
            raise ValueError("protocol_path is required for protocol mode")
        
        protocol_id = str(self.protocol_path)
        # Strip file extensions if present
        if protocol_id.endswith('.pdf'):
            protocol_id = protocol_id[:-4]
        # Get just the filename if it's a path
        protocol_id = Path(protocol_id).stem or protocol_id
        
        extractor = ProtocolSpecExtractor(protocol_id)
        spec = extractor.extract()
        self.assumptions = extractor.assumptions
        return spec
    
    def _resolve_from_custom(self) -> TrialDesignSpec:
        """Load spec purely from user-provided file or dict."""
        override_data = self._load_override_data()
        if override_data is None:
            raise ValueError("Custom mode requires override_path or override_dict")
        return TrialDesignSpec(**override_data)
    
    def _resolve_hybrid(self) -> TrialDesignSpec:
        """Merge protocol-extracted spec with user overrides."""
        # Start with protocol extraction
        if self.protocol_path is None:
            raise ValueError("protocol_path is required for hybrid mode")
        
        protocol_id = str(self.protocol_path)
        if protocol_id.endswith('.pdf'):
            protocol_id = protocol_id[:-4]
        protocol_id = Path(protocol_id).stem or protocol_id
        
        extractor = ProtocolSpecExtractor(protocol_id)
        base_spec = extractor.extract()
        self.assumptions = extractor.assumptions
        
        # Load overrides
        override_data = self._load_override_data()
        if override_data is None:
            # No overrides, return base spec
            return base_spec
        
        # Convert base spec to dict for merging
        base_dict = base_spec.model_dump()
        
        # Deep merge with overrides taking precedence
        merged_dict = self._deep_merge(base_dict, override_data)
        
        return TrialDesignSpec(**merged_dict)
    
    def _load_override_data(self) -> Optional[dict]:
        """Load override data from file or direct dict."""
        if self.override_dict is not None:
            return self.override_dict
        
        if self.override_path is None:
            return None
        
        path = Path(self.override_path)
        if not path.exists():
            raise FileNotFoundError(f"Override file not found: {path}")
        
        content = path.read_text()
        
        if path.suffix.lower() in ('.yaml', '.yml'):
            return yaml.safe_load(content)
        elif path.suffix.lower() == '.json':
            return json.loads(content)
        else:
            # Try YAML first, then JSON
            try:
                return yaml.safe_load(content)
            except yaml.YAMLError:
                return json.loads(content)
    
    def _deep_merge(self, base: dict, override: dict) -> dict:
        """
        Recursively merge override into base, with override taking precedence.
        
        For lists, performs keyed-merge using identifier fields:
        - arms: merged by 'armcd'
        - visits: merged by 'visitnum'
        - elements: merged by 'etcd'
        - arm_paths: merged by 'armcd'
        - Other lists: override replaces entirely
        
        Args:
            base: Base dictionary
            override: Override dictionary (wins on conflicts)
            
        Returns:
            Merged dictionary
        """
        result = base.copy()
        
        # Key fields for list merging
        list_key_fields = {
            'arms': 'armcd',
            'visits': 'visitnum',
            'elements': 'etcd',
            'arm_paths': 'armcd',
            'ts_parameters': 'tsparmcd',
        }
        
        for key, override_value in override.items():
            if key in result:
                base_value = result[key]
                
                # Both are dicts: recurse
                if isinstance(base_value, dict) and isinstance(override_value, dict):
                    result[key] = self._deep_merge(base_value, override_value)
                # Both are lists: keyed-merge if applicable
                elif isinstance(base_value, list) and isinstance(override_value, list):
                    if key in list_key_fields:
                        result[key] = self._merge_lists_by_key(
                            base_value, override_value, list_key_fields[key]
                        )
                    else:
                        # Unknown list type: override replaces entirely
                        result[key] = override_value
                else:
                    # Override wins
                    result[key] = override_value
            else:
                # New key from override
                result[key] = override_value
        
        return result
    
    def _merge_lists_by_key(self, base: list, override: list, key_field: str) -> list:
        """
        Merge two lists using a key field.
        
        Items in override with matching keys update base items.
        Items in override with new keys are appended.
        
        Args:
            base: Base list
            override: Override list
            key_field: Field name to use as key (e.g., 'armcd')
            
        Returns:
            Merged list
        """
        # Build index of base items by key
        base_by_key = {}
        for item in base:
            if isinstance(item, dict) and key_field in item:
                base_by_key[item[key_field]] = item
        
        # Build index of override items by key
        override_by_key = {}
        for item in override:
            if isinstance(item, dict) and key_field in item:
                override_by_key[item[key_field]] = item
        
        # Merge: start with base items, update with overrides
        result = []
        seen_keys = set()
        
        for item in base:
            if isinstance(item, dict) and key_field in item:
                key_val = item[key_field]
                seen_keys.add(key_val)
                if key_val in override_by_key:
                    # Merge the items (override wins on conflicts)
                    merged = {**item, **override_by_key[key_val]}
                    result.append(merged)
                else:
                    result.append(item)
            else:
                result.append(item)
        
        # Add override items with new keys
        for item in override:
            if isinstance(item, dict) and key_field in item:
                if item[key_field] not in seen_keys:
                    result.append(item)
            else:
                result.append(item)
        
        return result
    
    def get_assumptions(self) -> list:
        """Get list of assumptions made during spec extraction."""
        return self.assumptions


# ─── Contract 4: Spec Finalization ──────────────────────────────────────────

def _finalize_spec(spec: TrialDesignSpec) -> None:
    """Precompute and cache P_exp + pool_size at spec-resolution time (Contract 4).
    
    This runs ONCE per protocol. After finalization:
      - spec.ae_model.p_exp_by_sequence[seqcd] is set for every arm/sequence
      - spec.ae_model.min_p_exp is the worst-case P_exp across sequences
      - spec.ae_model.computed_pool_size is the auto-computed M (if not manually set)
    
    Raises ValueError if min_p_exp < 0.01 and allow_low_shaped_exposure_probability
    is not set. This prevents misconfigured specs from silently producing no AEs.
    """
    from ..core.canonical import ArmAssignment

    # ── Spec validation ──
    if not spec.arms:
        raise ValueError("Spec has no arms defined. At least one arm is required.")

    total = spec.compute_total_study_days()
    if total <= 0:
        raise ValueError(
            f"compute_total_study_days() returned {total}. "
            f"Check element durations in the spec."
        )

    disp = spec.disposition_model
    if disp.screen_fail_rate < 0 or disp.screen_fail_rate >= 1.0:
        raise ValueError(
            f"screen_fail_rate={disp.screen_fail_rate} is out of range [0, 1). "
            f"A value >= 1.0 would make every subject a screen failure."
        )
    if disp.completion_rate < 0 or disp.completion_rate > 1.0:
        raise ValueError(
            f"completion_rate={disp.completion_rate} is out of range [0, 1]."
        )

    a, b = spec.ae_model.time_shape_params
    
    MAX_FRAILTY_MULTIPLIER = 2.0  # match core/subject_generator constant
    
    def _compute_p_exp(treatment_sequence: List) -> float:
        """Compute P_exp for a single treatment sequence."""
        if a == 1.0 and b == 1.0:
            exposure_days = sum(
                (p.end_day if hasattr(p, 'end_day') else p['end_day']) -
                (p.start_day if hasattr(p, 'start_day') else p['start_day']) + 1
                for p in treatment_sequence
            )
            return max(exposure_days / total, 1e-6)
        
        if not HAS_SCIPY:
            exposure_days = sum(
                (p.end_day if hasattr(p, 'end_day') else p['end_day']) -
                (p.start_day if hasattr(p, 'start_day') else p['start_day']) + 1
                for p in treatment_sequence
            )
            return max(exposure_days / total, 1e-6)
        
        p_val = 0.0
        for period in treatment_sequence:
            start = period.start_day if hasattr(period, 'start_day') else period['start_day']
            end = period.end_day if hasattr(period, 'end_day') else period['end_day']
            lo = (start - 1) / total
            hi = end / total
            p_val += beta_dist.cdf(hi, a, b) - beta_dist.cdf(lo, a, b)
        return max(p_val, 1e-6)
    
    # Build treatment sequences and compute P_exp for each
    p_exp_map = {}
    
    if spec.is_crossover and spec.crossover_sequences:
        for seq_def in spec.crossover_sequences:
            seqcd = seq_def['seqcd'] if isinstance(seq_def, dict) else seq_def.seqcd
            periods_data = seq_def['periods'] if isinstance(seq_def, dict) else seq_def.periods
            ts = []
            for p in periods_data:
                if isinstance(p, dict):
                    ts.append(ArmAssignment(
                        period=p['period'], armcd=p['armcd'],
                        epoch_label=p.get('epoch', ''),
                        start_day=p['start_day'], end_day=p['end_day'],
                    ))
                else:
                    ts.append(p)
            p_exp_map[seqcd] = _compute_p_exp(ts)
    else:
        for arm in spec.arms:
            ts = _build_arm_treatment_sequence(spec, arm.armcd)
            p_exp_map[arm.armcd] = _compute_p_exp(ts)
    
    if not p_exp_map:
        p_exp_map["DEFAULT"] = 1.0
    
    worst = min(p_exp_map.values())
    
    # Contract 4: raise ValueError for near-zero P_exp unless overridden
    if worst < 0.01 and not getattr(spec, 'allow_low_shaped_exposure_probability', False):
        raise ValueError(
            f"min_shaped_exposure_probability = {worst:.6f} < 0.01. "
            f"This will cause pool exhaustion or near-zero AE yield. "
            f"Check exposure windows vs total_study_days={total}. "
            f"Set spec.allow_low_shaped_exposure_probability = True to override."
        )
    
    # Cache onto spec
    spec.ae_model.p_exp_by_sequence = p_exp_map
    spec.ae_model.min_p_exp = worst
    
    # Compute pool size if not manually set
    if spec.ae_model.pool_size <= 0:
        max_exposure_months = total / 30.0
        lambda_eff_max = (
            spec.ae_model.ae_rate_multiplier
            * max_exposure_months
            * MAX_FRAILTY_MULTIPLIER
        ) / worst
        M = math.ceil(lambda_eff_max + 6 * math.sqrt(max(lambda_eff_max, 1)))
        spec.ae_model.computed_pool_size = max(M, 30)
    else:
        spec.ae_model.computed_pool_size = spec.ae_model.pool_size


def _build_arm_treatment_sequence(spec: TrialDesignSpec, armcd: str) -> List:
    """Build treatment sequence for a parallel arm from spec paths."""
    from ..core.canonical import ArmAssignment
    
    for path in spec.arm_paths:
        if path.armcd == armcd:
            ts = []
            cum_day = 1
            for item in path.elements:
                elem = next((e for e in spec.elements if e.etcd == item.etcd), None)
                if elem:
                    dur = elem.nominal_duration_days
                    if elem.epoch.upper() in ('TREATMENT',):
                        ts.append(ArmAssignment(
                            period=1, armcd=armcd,
                            epoch_label=elem.epoch,
                            start_day=cum_day,
                            end_day=cum_day + dur - 1,
                        ))
                    cum_day += dur
            if ts:
                return ts
    
    # Fallback: treat entire study as exposure
    return [ArmAssignment(period=1, armcd=armcd, epoch_label='TREATMENT',
               start_day=1, end_day=max(spec.compute_total_study_days(), 1))]


def load_spec_from_yaml(path: Union[str, Path]) -> TrialDesignSpec:
    """
    Load a TrialDesignSpec from a YAML file.

    Runs _finalize_spec() to compute AE pool sizing and validate
    structural constraints, same as the protocol-extraction path.

    Args:
        path: Path to YAML file

    Returns:
        TrialDesignSpec instance (finalized)
    """
    path = Path(path)
    content = path.read_text()
    data = yaml.safe_load(content)
    spec = TrialDesignSpec(**data)
    _finalize_spec(spec)
    return spec


def save_spec_to_yaml(spec: TrialDesignSpec, path: Union[str, Path]) -> None:
    """
    Save a TrialDesignSpec to a YAML file.
    
    Args:
        spec: TrialDesignSpec to save
        path: Output path
    """
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    
    # Convert to dict, excluding None values for cleaner output
    data = spec.model_dump(exclude_none=True)
    
    with open(path, 'w') as f:
        yaml.dump(data, f, default_flow_style=False, sort_keys=False, allow_unicode=True)


def save_spec_to_json(spec: TrialDesignSpec, path: Union[str, Path], indent: int = 2) -> None:
    """
    Save a TrialDesignSpec to a JSON file.
    
    Args:
        spec: TrialDesignSpec to save
        path: Output path
        indent: JSON indentation level
    """
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    
    data = spec.model_dump(exclude_none=True)
    
    with open(path, 'w') as f:
        json.dump(data, f, indent=indent, default=str)
