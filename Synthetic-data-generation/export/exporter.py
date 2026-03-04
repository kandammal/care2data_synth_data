"""
SDTM Synthetic Data Generator - Exporter

This module exports SDTM datasets to CSV files.
"""

from __future__ import annotations
from typing import List, Dict, Optional
from pathlib import Path
import pandas as pd


# Standard domain output order per SDTM
DOMAIN_ORDER = [
    'TE',  # Trial Elements
    'TA',  # Trial Arms
    'TS',  # Trial Summary
    'TV',  # Trial Visits
    'DM',  # Demographics
    'MH',  # Medical History
    'SE',  # Subject Elements
    'SV',  # Subject Visits
    'DS',  # Disposition
    'EX',  # Exposure
    'CM',  # Concomitant Medications
    'VS',  # Vital Signs
    'LB',  # Laboratory
    'AE',  # Adverse Events
    'RELREC',  # Related Records (special-purpose)
]


class SDTMExporter:
    """
    Exports SDTM datasets to CSV files.
    
    Features:
    - Export in standard domain order
    - Optional domain filtering
    - UTF-8 encoding
    - ISO 8601 date formatting
    """
    
    def __init__(self, output_dir: Optional[Path] = None):
        """
        Initialize the exporter.
        
        Args:
            output_dir: Output directory (defaults to current directory)
        """
        self.output_dir = Path(output_dir) if output_dir else Path('.')
    
    def export_all(
        self, 
        datasets: Dict[str, pd.DataFrame],
        domains: Optional[List[str]] = None,
        prefix: str = ''
    ) -> List[Path]:
        """
        Export all datasets to CSV files.
        
        Args:
            datasets: Dict mapping domain name to DataFrame
            domains: Optional list of domains to export (None = all)
            prefix: Optional prefix for filenames
            
        Returns:
            List of exported file paths
        """
        # Ensure output directory exists
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # Determine which domains to export
        if domains:
            export_domains = [d for d in DOMAIN_ORDER if d in domains]
        else:
            export_domains = [d for d in DOMAIN_ORDER if d in datasets]
        
        exported_files = []
        
        for domain in export_domains:
            if domain in datasets:
                filepath = self.export_domain(datasets[domain], domain, prefix)
                exported_files.append(filepath)
        
        return exported_files
    
    def export_domain(
        self, 
        df: pd.DataFrame, 
        domain: str,
        prefix: str = ''
    ) -> Path:
        """
        Export a single domain to CSV.
        
        Args:
            df: DataFrame to export
            domain: Domain name
            prefix: Optional filename prefix
            
        Returns:
            Path to exported file
        """
        # Build filename
        if prefix:
            filename = f"{prefix}_{domain.lower()}.csv"
        else:
            filename = f"{domain.lower()}.csv"
        
        filepath = self.output_dir / filename
        
        # Export to CSV
        # Issue 6 fix: sanitize NaN/None → "" before writing to prevent
        # RuntimeWarning: invalid value encountered in cast
        clean_df = df.astype(object).where(pd.notna(df), "")
        clean_df.to_csv(
            filepath,
            index=False,
            encoding='utf-8',
            na_rep='',
            date_format='%Y-%m-%d'
        )
        
        return filepath
    
    def export_combined(
        self, 
        datasets: Dict[str, pd.DataFrame],
        filename: str = 'sdtm_combined.csv',
        prefix: str = ''
    ) -> Path:
        """
        Export all datasets to a single combined CSV with domain column.
        
        Args:
            datasets: Dict mapping domain name to DataFrame
            filename: Output filename
            prefix: Optional filename prefix
            
        Returns:
            Path to exported file
        """
        # Ensure output directory exists
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # Build filename
        if prefix:
            filename = f"{prefix}_{filename}"
        
        filepath = self.output_dir / filename
        
        # Combine datasets
        combined_dfs = []
        
        for domain in DOMAIN_ORDER:
            if domain in datasets:
                df = datasets[domain].copy()
                if 'DOMAIN' not in df.columns:
                    df.insert(1, 'DOMAIN', domain)
                combined_dfs.append(df)
        
        if combined_dfs:
            combined = pd.concat(combined_dfs, ignore_index=True, sort=False)
            combined = combined.astype(object).where(pd.notna(combined), "")
            combined.to_csv(filepath, index=False, encoding='utf-8', na_rep='')
        
        return filepath


def export_datasets(
    datasets: Dict[str, pd.DataFrame],
    output_dir: Path,
    prefix: str = '',
    domains: Optional[List[str]] = None
) -> List[Path]:
    """
    Convenience function to export datasets.
    
    Args:
        datasets: Dict mapping domain name to DataFrame
        output_dir: Output directory
        prefix: Optional filename prefix
        domains: Optional list of domains to export
        
    Returns:
        List of exported file paths
    """
    exporter = SDTMExporter(output_dir)
    return exporter.export_all(datasets, domains=domains, prefix=prefix)
