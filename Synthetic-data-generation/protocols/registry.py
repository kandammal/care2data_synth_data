"""
Protocol Registry

Central registry for known protocol specifications and auto-detection.
"""

from typing import Dict, Any, Optional, List
from dataclasses import dataclass
from pathlib import Path


# =============================================================================
# KNOWN PROTOCOL SPECIFICATIONS
# =============================================================================

KNOWN_PROTOCOLS: Dict[str, Dict[str, Any]] = {
    
    # -------------------------------------------------------------------------
    # TJ301 (Olamkicept) - Ulcerative Colitis Phase 2
    # Protocol: CTJ301UC201 (Prot_000)
    # -------------------------------------------------------------------------
    'tj301': {
        'protocol_id': 'CTJ301UC201',
        'study_title': 'A Phase II, Randomized, Double-blind, Placebo-controlled Study to Evaluate the Safety and Efficacy of TJ301 (Olamkicept) in Patients with Active Ulcerative Colitis',
        'phase': '2',
        'blinding': 'double_blind',
        'indication': 'Active Ulcerative Colitis',
        'sponsor': 'Leading Biopharm Limited',
        
        'arms': [
            {
                'name': 'TJ301_600MG',
                'regimen': [{
                    'drug': 'TJ301',
                    'dose': 600,
                    'dose_unit': 'mg',
                    'frequency': 'Q2W',
                    'route': 'INTRAVENOUS',
                    'duration_days': 84,  # 12 weeks
                    'dosage_form': 'INJECTION',
                }]
            },
            {
                'name': 'TJ301_300MG',
                'regimen': [{
                    'drug': 'TJ301',
                    'dose': 300,
                    'dose_unit': 'mg',
                    'frequency': 'Q2W',
                    'route': 'INTRAVENOUS',
                    'duration_days': 84,
                    'dosage_form': 'INJECTION',
                }]
            },
            {
                'name': 'PLACEBO',
                'regimen': [{
                    'drug': 'PLACEBO',
                    'dose': 0,
                    'dose_unit': 'mg',
                    'frequency': 'Q2W',
                    'route': 'INTRAVENOUS',
                    'duration_days': 84,
                    'dosage_form': 'INJECTION',
                }]
            },
        ],
        
        'visits': [
            {'name': 'SCREENING', 'day': -28, 'window_before': 0, 'window_after': 27},
            {'name': 'BASELINE', 'day': 1, 'window_before': 0, 'window_after': 0},
            {'name': 'WEEK 2', 'day': 15, 'window_before': 3, 'window_after': 3},
            {'name': 'WEEK 4', 'day': 29, 'window_before': 3, 'window_after': 3},
            {'name': 'WEEK 6', 'day': 43, 'window_before': 3, 'window_after': 3},
            {'name': 'WEEK 8', 'day': 57, 'window_before': 3, 'window_after': 3},
            {'name': 'WEEK 10', 'day': 71, 'window_before': 3, 'window_after': 3},
            {'name': 'WEEK 12', 'day': 85, 'window_before': 3, 'window_after': 3},
            {'name': 'FOLLOW-UP', 'day': 105, 'window_before': 3, 'window_after': 7},
        ],
        
        'demographics': {
            'age_min': 18,
            'age_max': 70,
            'total_subjects': 90,
            'subjects_per_arm': {'TJ301_600MG': 30, 'TJ301_300MG': 30, 'PLACEBO': 30},
            'sex_distribution': {'M': 0.55, 'F': 0.45},
            'race_distribution': {
                'ASIAN': 0.70,
                'WHITE': 0.20,
                'OTHER': 0.10
            },
            'country': 'CHN',
            'sites': ['SITE001', 'SITE002', 'SITE003', 'SITE004', 'SITE005'],
        },
        
        'treatment_duration_weeks': 12,
        'follow_up_weeks': 5,
    },
    
    # -------------------------------------------------------------------------
    # Teplizumab (PRV-031) - Type 1 Diabetes Phase 3 (PROTECT)
    # Protocol: PRV-031-001 (Prot_002)
    # -------------------------------------------------------------------------
    'protect': {
        'protocol_id': 'PRV-031-001',
        'study_title': 'PROTECT: A Phase 3, Randomized, Double-Blind, Placebo-Controlled Study to Evaluate Efficacy and Safety of Teplizumab in Children and Adolescents with Newly Diagnosed Type 1 Diabetes',
        'phase': '3',
        'blinding': 'double_blind',
        'indication': 'Newly Diagnosed Type 1 Diabetes',
        'sponsor': 'Provention Bio, Inc.',
        
        'arms': [
            {
                'name': 'TEPLIZUMAB',
                'regimen': [{
                    'drug': 'TEPLIZUMAB',
                    'dose': 9.14,  # Escalating dose, this is cumulative over 12 days
                    'dose_unit': 'ug/m2',
                    'frequency': 'DAILY',  # 12-day courses
                    'route': 'INTRAVENOUS',
                    'duration_days': 12,  # Each course
                    'dosage_form': 'INJECTION',
                }]
            },
            {
                'name': 'PLACEBO',
                'regimen': [{
                    'drug': 'PLACEBO',
                    'dose': 0,
                    'dose_unit': 'mg',
                    'frequency': 'DAILY',
                    'route': 'INTRAVENOUS',
                    'duration_days': 12,
                    'dosage_form': 'INJECTION',
                }]
            },
        ],
        
        'visits': [
            {'name': 'SCREENING', 'day': -42, 'window_before': 0, 'window_after': 42},
            {'name': 'BASELINE', 'day': 1, 'window_before': 0, 'window_after': 0},
            {'name': 'COURSE 1 END', 'day': 12, 'window_before': 0, 'window_after': 2},
            {'name': 'WEEK 6', 'day': 43, 'window_before': 7, 'window_after': 7},
            {'name': 'WEEK 13', 'day': 92, 'window_before': 7, 'window_after': 7},
            {'name': 'WEEK 20', 'day': 141, 'window_before': 7, 'window_after': 7},
            {'name': 'WEEK 26 (COURSE 2)', 'day': 182, 'window_before': 7, 'window_after': 7},
            {'name': 'COURSE 2 END', 'day': 194, 'window_before': 0, 'window_after': 2},
            {'name': 'WEEK 39', 'day': 274, 'window_before': 7, 'window_after': 7},
            {'name': 'WEEK 52', 'day': 365, 'window_before': 7, 'window_after': 7},
            {'name': 'WEEK 65', 'day': 456, 'window_before': 7, 'window_after': 7},
            {'name': 'WEEK 78', 'day': 547, 'window_before': 7, 'window_after': 14},
        ],
        
        'demographics': {
            'age_min': 8,
            'age_max': 17,
            'total_subjects': 300,
            'subjects_per_arm': {'TEPLIZUMAB': 200, 'PLACEBO': 100},
            'sex_distribution': {'M': 0.52, 'F': 0.48},
            'race_distribution': {
                'WHITE': 0.75,
                'BLACK OR AFRICAN AMERICAN': 0.10,
                'ASIAN': 0.05,
                'OTHER': 0.10
            },
            'country': 'USA',
            'sites': ['SITE' + str(i).zfill(3) for i in range(1, 51)],  # 50 sites
        },
        
        'treatment_duration_weeks': 26,
        'follow_up_weeks': 52,
    },
    
    # -------------------------------------------------------------------------
    # Sutimlimab - Cold Agglutinin Disease (LTS Japan Extension)
    # Protocol: LTS17352 (Prot_003)
    # -------------------------------------------------------------------------
    'sutimlimab': {
        'protocol_id': 'LTS17352',
        'study_title': 'An Open-Label Study for Sutimlimab in Participants with Cold Agglutinin Disease (CAD) Who Have Completed the CARDINAL or CADENZA Study in Japan',
        'phase': '3',
        'blinding': 'open_label',
        'indication': 'Cold Agglutinin Disease',
        'sponsor': 'Sanofi K.K.',
        
        'arms': [
            {
                'name': 'SUTIMLIMAB',
                'regimen': [{
                    'drug': 'SUTIMLIMAB',
                    'dose': 6500,  # Weight-based: 6.5g for <75kg, 7.5g for ≥75kg
                    'dose_unit': 'mg',
                    'frequency': 'Q2W',
                    'route': 'INTRAVENOUS',
                    'duration_days': 728,  # 2 years extension
                    'dosage_form': 'INJECTION',
                }]
            },
        ],
        
        'visits': [
            {'name': 'BASELINE', 'day': 1, 'window_before': 0, 'window_after': 0},
            {'name': 'WEEK 2', 'day': 15, 'window_before': 3, 'window_after': 3},
            {'name': 'WEEK 4', 'day': 29, 'window_before': 3, 'window_after': 3},
            {'name': 'WEEK 8', 'day': 57, 'window_before': 7, 'window_after': 7},
            {'name': 'WEEK 12', 'day': 85, 'window_before': 7, 'window_after': 7},
            {'name': 'WEEK 24', 'day': 169, 'window_before': 7, 'window_after': 7},
            {'name': 'WEEK 36', 'day': 253, 'window_before': 7, 'window_after': 7},
            {'name': 'WEEK 52', 'day': 365, 'window_before': 14, 'window_after': 14},
        ],
        
        'demographics': {
            'age_min': 18,
            'age_max': 85,
            'total_subjects': 20,  # Small extension in Japan
            'subjects_per_arm': {'SUTIMLIMAB': 20},
            'sex_distribution': {'M': 0.40, 'F': 0.60},  # CAD more common in women
            'race_distribution': {'ASIAN': 1.0},  # Japan only
            'country': 'JPN',
            'sites': ['TOKYO01', 'OSAKA01', 'NAGOYA01'],
        },
        
        'treatment_duration_weeks': 104,
        'follow_up_weeks': 4,
    },
    
    # -------------------------------------------------------------------------
    # BENDITA (existing) - Chagas Disease
    # -------------------------------------------------------------------------
    'bendita': {
        'protocol_id': 'DNDi-CH-BENDITA-001',
        'study_title': 'BENDITA: Benznidazole New Doses Improved Treatment and Associations',
        'phase': '2',
        'blinding': 'double_blind',
        'indication': 'Chronic Chagas Disease',
        'sponsor': 'DNDi',
        
        'arms': [
            {
                'name': 'BNZ_300MG_8W',
                'regimen': [{
                    'drug': 'BENZNIDAZOLE',
                    'dose': 300,
                    'dose_unit': 'mg',
                    'frequency': 'QD',
                    'route': 'ORAL',
                    'duration_days': 56,
                    'dosage_form': 'TABLET',
                }]
            },
            {
                'name': 'BNZ_150MG_4W',
                'regimen': [{
                    'drug': 'BENZNIDAZOLE',
                    'dose': 150,
                    'dose_unit': 'mg',
                    'frequency': 'QD',
                    'route': 'ORAL',
                    'duration_days': 28,
                    'dosage_form': 'TABLET',
                }]
            },
            {
                'name': 'PLACEBO',
                'regimen': [{
                    'drug': 'PLACEBO',
                    'dose': 0,
                    'dose_unit': 'mg',
                    'frequency': 'QD',
                    'route': 'ORAL',
                    'duration_days': 56,
                    'dosage_form': 'TABLET',
                }]
            },
        ],
        
        'visits': [
            {'name': 'SCREENING', 'day': -30, 'window_before': 0, 'window_after': 30},
            {'name': 'BASELINE', 'day': 1, 'window_before': 0, 'window_after': 0},
            {'name': 'WEEK 2', 'day': 15, 'window_before': 3, 'window_after': 3},
            {'name': 'WEEK 4', 'day': 29, 'window_before': 3, 'window_after': 3},
            {'name': 'WEEK 8', 'day': 57, 'window_before': 3, 'window_after': 3},
            {'name': 'MONTH 4', 'day': 120, 'window_before': 7, 'window_after': 7},
            {'name': 'MONTH 6', 'day': 180, 'window_before': 7, 'window_after': 7},
            {'name': 'MONTH 12', 'day': 365, 'window_before': 14, 'window_after': 14},
        ],
        
        'demographics': {
            'age_min': 18,
            'age_max': 60,
            'total_subjects': 210,
            'subjects_per_arm': {'BNZ_300MG_8W': 70, 'BNZ_150MG_4W': 70, 'PLACEBO': 70},
            'sex_distribution': {'M': 0.45, 'F': 0.55},
            'race_distribution': {
                'WHITE': 0.30,
                'AMERICAN INDIAN OR ALASKA NATIVE': 0.40,
                'OTHER': 0.30
            },
            'country': 'BOL',
            'sites': ['SUCRE01', 'TARIJA01', 'COCHABAMBA01'],
        },
        
        'treatment_duration_weeks': 8,
        'follow_up_weeks': 44,
    },
    
    # -------------------------------------------------------------------------
    # HS-11-421 (existing) - Psoriatic Arthritis
    # -------------------------------------------------------------------------
    'hs11421': {
        'protocol_id': 'HS-11-421',
        'study_title': 'A Phase 3 Study of Subcutaneous Secukinumab in Patients with Psoriatic Arthritis',
        'phase': '3',
        'blinding': 'double_blind',
        'indication': 'Psoriatic Arthritis',
        'sponsor': 'Novartis',
        
        'arms': [
            {
                'name': 'SECUKINUMAB_300MG',
                'regimen': [{
                    'drug': 'SECUKINUMAB',
                    'dose': 300,
                    'dose_unit': 'mg',
                    'frequency': 'QW',  # Weekly for loading, then Q4W
                    'route': 'SUBCUTANEOUS',
                    'duration_days': 336,  # 48 weeks
                    'dosage_form': 'INJECTION',
                }]
            },
            {
                'name': 'SECUKINUMAB_150MG',
                'regimen': [{
                    'drug': 'SECUKINUMAB',
                    'dose': 150,
                    'dose_unit': 'mg',
                    'frequency': 'QW',
                    'route': 'SUBCUTANEOUS',
                    'duration_days': 336,
                    'dosage_form': 'INJECTION',
                }]
            },
            {
                'name': 'PLACEBO',
                'regimen': [{
                    'drug': 'PLACEBO',
                    'dose': 0,
                    'dose_unit': 'mg',
                    'frequency': 'QW',
                    'route': 'SUBCUTANEOUS',
                    'duration_days': 168,  # Crosses to active at Week 24
                    'dosage_form': 'INJECTION',
                }]
            },
        ],
        
        'visits': [
            {'name': 'SCREENING', 'day': -28, 'window_before': 0, 'window_after': 28},
            {'name': 'BASELINE', 'day': 1, 'window_before': 0, 'window_after': 0},
            {'name': 'WEEK 1', 'day': 8, 'window_before': 2, 'window_after': 2},
            {'name': 'WEEK 2', 'day': 15, 'window_before': 2, 'window_after': 2},
            {'name': 'WEEK 3', 'day': 22, 'window_before': 2, 'window_after': 2},
            {'name': 'WEEK 4', 'day': 29, 'window_before': 3, 'window_after': 3},
            {'name': 'WEEK 8', 'day': 57, 'window_before': 5, 'window_after': 5},
            {'name': 'WEEK 12', 'day': 85, 'window_before': 5, 'window_after': 5},
            {'name': 'WEEK 16', 'day': 113, 'window_before': 5, 'window_after': 5},
            {'name': 'WEEK 24', 'day': 169, 'window_before': 7, 'window_after': 7},
            {'name': 'WEEK 36', 'day': 253, 'window_before': 7, 'window_after': 7},
            {'name': 'WEEK 48', 'day': 337, 'window_before': 7, 'window_after': 7},
        ],
        
        'demographics': {
            'age_min': 18,
            'age_max': 75,
            'total_subjects': 420,
            'subjects_per_arm': {'SECUKINUMAB_300MG': 140, 'SECUKINUMAB_150MG': 140, 'PLACEBO': 140},
            'sex_distribution': {'M': 0.50, 'F': 0.50},
            'race_distribution': {
                'WHITE': 0.85,
                'ASIAN': 0.08,
                'BLACK OR AFRICAN AMERICAN': 0.04,
                'OTHER': 0.03
            },
            'country': 'USA',
            'sites': ['SITE' + str(i).zfill(3) for i in range(1, 31)],
        },
        
        'treatment_duration_weeks': 48,
        'follow_up_weeks': 8,
    },
    
    # -------------------------------------------------------------------------
    # HERALD (existing) - COVID-19 Vaccine
    # -------------------------------------------------------------------------
    'herald': {
        'protocol_id': 'CV-NCOV-004',
        'study_title': 'HERALD: COVID-19 Vaccine Phase 3 Trial',
        'phase': '3',
        'blinding': 'double_blind',
        'indication': 'COVID-19 Prevention',
        'sponsor': 'Janssen',
        
        'arms': [
            {
                'name': 'VACCINE',
                'regimen': [{
                    'drug': 'AD26.COV2.S',
                    'dose': 5e10,  # viral particles
                    'dose_unit': 'vp',
                    'frequency': 'ONCE',
                    'route': 'INTRAMUSCULAR',
                    'duration_days': 1,
                    'dosage_form': 'INJECTION',
                }]
            },
            {
                'name': 'PLACEBO',
                'regimen': [{
                    'drug': 'PLACEBO',
                    'dose': 0,
                    'dose_unit': 'mL',
                    'frequency': 'ONCE',
                    'route': 'INTRAMUSCULAR',
                    'duration_days': 1,
                    'dosage_form': 'INJECTION',
                }]
            },
        ],
        
        'visits': [
            {'name': 'SCREENING', 'day': -28, 'window_before': 0, 'window_after': 28},
            {'name': 'DAY 1 (VACCINATION)', 'day': 1, 'window_before': 0, 'window_after': 0},
            {'name': 'DAY 29', 'day': 29, 'window_before': 3, 'window_after': 7},
            {'name': 'DAY 71', 'day': 71, 'window_before': 7, 'window_after': 14},
            {'name': 'DAY 183', 'day': 183, 'window_before': 14, 'window_after': 14},
            {'name': 'DAY 365', 'day': 365, 'window_before': 14, 'window_after': 28},
        ],
        
        'demographics': {
            'age_min': 18,
            'age_max': 85,
            'total_subjects': 44000,
            'subjects_per_arm': {'VACCINE': 22000, 'PLACEBO': 22000},
            'sex_distribution': {'M': 0.55, 'F': 0.45},
            'race_distribution': {
                'WHITE': 0.60,
                'BLACK OR AFRICAN AMERICAN': 0.17,
                'ASIAN': 0.04,
                'AMERICAN INDIAN OR ALASKA NATIVE': 0.01,
                'OTHER': 0.18
            },
            'country': 'USA',
            'sites': ['SITE' + str(i).zfill(4) for i in range(1, 201)],
        },
        
        'treatment_duration_weeks': 0,  # Single vaccination
        'follow_up_weeks': 52,
    },
    
    # -------------------------------------------------------------------------
    # BDA (Budesonide/Albuterol MDI) - Exercise-Induced Bronchoconstriction
    # Protocol: AV005 / TYREE (Prot_008)
    # 2×2 crossover, single-dose per period
    # -------------------------------------------------------------------------
    'bda': {
        'protocol_id': 'AV005',
        'study_title': 'TYREE: A Randomized, Double-blind, Single-Dose, 2-Period, Crossover Study to Assess the Efficacy of PT027 (BDA MDI) Compared with Placebo on Exercise-Induced Bronchoconstriction',
        'phase': '3',
        'blinding': 'double_blind',
        'indication': 'Exercise-Induced Bronchoconstriction in Asthma',
        'sponsor': 'Bond Avillion 2 Development LP',
        'is_crossover': True,
        
        'arms': [
            {
                'name': 'BDA_MDI',
                'regimen': [{
                    'drug': 'BDA MDI 160/180 MCG',
                    'dose': 160,
                    'dose_unit': 'mcg',
                    'frequency': 'ONCE',
                    'route': 'INHALATION',
                    'duration_days': 1,
                    'dosage_form': 'METERED DOSE INHALER',
                }]
            },
            {
                'name': 'PLACEBO',
                'regimen': [{
                    'drug': 'PLACEBO MDI',
                    'dose': 0,
                    'dose_unit': 'mcg',
                    'frequency': 'ONCE',
                    'route': 'INHALATION',
                    'duration_days': 1,
                    'dosage_form': 'METERED DOSE INHALER',
                }]
            },
        ],
        
        # 2×2 crossover sequences
        'crossover_sequences': [
            {
                'seqcd': 'AB',
                'label': 'Sequence AB: BDA then Placebo',
                'periods': [
                    {'period': 1, 'armcd': 'BDA_MDI', 'epoch': 'PERIOD 1',
                     'start_day': 1, 'end_day': 1, 'washout_days_before': 0},
                    {'period': 2, 'armcd': 'PLACEBO', 'epoch': 'PERIOD 2',
                     'start_day': 8, 'end_day': 8, 'washout_days_before': 7},
                ]
            },
            {
                'seqcd': 'BA',
                'label': 'Sequence BA: Placebo then BDA',
                'periods': [
                    {'period': 1, 'armcd': 'PLACEBO', 'epoch': 'PERIOD 1',
                     'start_day': 1, 'end_day': 1, 'washout_days_before': 0},
                    {'period': 2, 'armcd': 'BDA_MDI', 'epoch': 'PERIOD 2',
                     'start_day': 8, 'end_day': 8, 'washout_days_before': 7},
                ]
            },
        ],
        
        'visits': [
            {'name': 'SCREENING (V1)', 'day': -14, 'window_before': 0, 'window_after': 7},
            {'name': 'EIB CONFIRMATION (V2)', 'day': -7, 'window_before': 3, 'window_after': 3},
            {'name': 'PERIOD 1 (V3)', 'day': 1, 'window_before': 0, 'window_after': 0},
            {'name': 'PERIOD 2 (V4)', 'day': 8, 'window_before': 2, 'window_after': 2},
            {'name': 'FOLLOW-UP (TC)', 'day': 12, 'window_before': 0, 'window_after': 2},
        ],
        
        'demographics': {
            'age_min': 12,
            'age_max': 70,
            'age_mean': 35,
            'age_sd': 14,
            'total_subjects': 60,
            'subjects_per_arm': {'AB': 30, 'BA': 30},
            'sex_distribution': {'M': 0.45, 'F': 0.55},
            'race_distribution': {
                'WHITE': 0.70, 'BLACK OR AFRICAN AMERICAN': 0.15,
                'ASIAN': 0.08, 'OTHER': 0.07
            },
            'country': 'USA',
            'sites': ['SITE001', 'SITE002', 'SITE003', 'SITE004', 'SITE005', 'SITE006'],
            'screen_fail_rate': 0.50,
        },
        
        'total_study_days': 12,
        'treatment_duration_weeks': 0,  # single dose per period
        'follow_up_weeks': 1,
    },
    
    # -------------------------------------------------------------------------
    # USL261 (Intranasal Midazolam) - Seizure Clusters Safety Extension
    # Protocol: P261-402 / ARTEMIS Extension (Prot_009)
    # Open-label, single-arm, event-driven dosing
    # -------------------------------------------------------------------------
    'usl261': {
        'protocol_id': 'P261-402',
        'study_title': 'An Open-Label Safety Study of USL261 in the Outpatient Treatment of Subjects with Seizure Clusters',
        'phase': '3',
        'blinding': 'open_label',
        'indication': 'Seizure Clusters (Acute Repetitive Seizures)',
        'sponsor': 'Upsher-Smith Laboratories, Inc.',
        'is_crossover': False,
        
        'arms': [
            {
                'name': 'USL261_5MG',
                'regimen': [{
                    'drug': 'USL261 5 MG',
                    'dose': 5.0,
                    'dose_unit': 'mg',
                    'frequency': 'PRN',
                    'route': 'NASAL',
                    'duration_days': 365,
                    'dosage_form': 'SPRAY',
                }]
            },
        ],
        
        'visits': [
            {'name': 'VISIT 1 (ENROLLMENT)', 'day': 1, 'window_before': 0, 'window_after': 0},
            {'name': 'VISIT 2', 'day': 90, 'window_before': 5, 'window_after': 5},
            {'name': 'VISIT 3', 'day': 180, 'window_before': 14, 'window_after': 14},
            {'name': 'VISIT 4', 'day': 270, 'window_before': 14, 'window_after': 14},
            {'name': 'VISIT 5', 'day': 365, 'window_before': 14, 'window_after': 14},
            {'name': 'FINAL VISIT', 'day': 450, 'window_before': 14, 'window_after': 28},
        ],
        
        'demographics': {
            'age_min': 12,
            'age_max': 85,
            'age_mean': 40,
            'age_sd': 18,
            'total_subjects': 240,
            'subjects_per_arm': {'USL261_5MG': 240},
            'sex_distribution': {'M': 0.48, 'F': 0.52},
            'race_distribution': {
                'WHITE': 0.72, 'BLACK OR AFRICAN AMERICAN': 0.12,
                'ASIAN': 0.06, 'OTHER': 0.10
            },
            'country': 'USA',
            'sites': ['SITE' + str(i).zfill(3) for i in range(1, 31)],
            'screen_fail_rate': 0.05,
        },
        
        'total_study_days': 450,
        'treatment_duration_weeks': 52,
        'follow_up_weeks': 12,
    },
    
    # -------------------------------------------------------------------------
    # KONFIDENT (KVD900) - Hereditary Angioedema On-Demand Treatment
    # Protocol: KVD900-301 (Prot_010)
    # 3-way crossover, 6 sequences, attack-driven dosing
    # -------------------------------------------------------------------------
    'konfident': {
        'protocol_id': 'KVD900-301',
        'study_title': 'KONFIDENT: A Phase 3, Three-way Crossover Trial to Evaluate KVD900 for On-Demand Treatment of HAE Attacks',
        'phase': '3',
        'blinding': 'double_blind',
        'indication': 'Hereditary Angioedema Type I or II',
        'sponsor': 'KalVista Pharmaceuticals Ltd',
        'is_crossover': True,
        
        'arms': [
            {
                'name': 'KVD900_600MG',
                'regimen': [{
                    'drug': 'KVD900 600 MG',
                    'dose': 600,
                    'dose_unit': 'mg',
                    'frequency': 'PRN',
                    'route': 'ORAL',
                    'duration_days': 1,
                    'dosage_form': 'TABLET, FILM COATED',
                }]
            },
            {
                'name': 'KVD900_300MG',
                'regimen': [{
                    'drug': 'KVD900 300 MG',
                    'dose': 300,
                    'dose_unit': 'mg',
                    'frequency': 'PRN',
                    'route': 'ORAL',
                    'duration_days': 1,
                    'dosage_form': 'TABLET, FILM COATED',
                }]
            },
            {
                'name': 'PLACEBO',
                'regimen': [{
                    'drug': 'PLACEBO',
                    'dose': 0,
                    'dose_unit': 'mg',
                    'frequency': 'PRN',
                    'route': 'ORAL',
                    'duration_days': 1,
                    'dosage_form': 'TABLET',
                }]
            },
        ],
        
        # 3-way crossover: 6 sequences (ABC, ACB, BAC, BCA, CAB, CBA)
        # A=KVD900 600mg, B=KVD900 300mg, C=Placebo
        # Each "period" is treating an attack; ~48h washout between attacks
        # Modeled as 3 periods with ~6-week spacing for attack occurrence
        'crossover_sequences': [
            {
                'seqcd': 'ABC',
                'label': 'Sequence ABC: 600mg then 300mg then Placebo',
                'periods': [
                    {'period': 1, 'armcd': 'KVD900_600MG', 'epoch': 'PERIOD 1',
                     'start_day': 1, 'end_day': 42, 'washout_days_before': 0},
                    {'period': 2, 'armcd': 'KVD900_300MG', 'epoch': 'PERIOD 2',
                     'start_day': 44, 'end_day': 86, 'washout_days_before': 2},
                    {'period': 3, 'armcd': 'PLACEBO', 'epoch': 'PERIOD 3',
                     'start_day': 88, 'end_day': 130, 'washout_days_before': 2},
                ]
            },
            {
                'seqcd': 'ACB',
                'label': 'Sequence ACB: 600mg then Placebo then 300mg',
                'periods': [
                    {'period': 1, 'armcd': 'KVD900_600MG', 'epoch': 'PERIOD 1',
                     'start_day': 1, 'end_day': 42, 'washout_days_before': 0},
                    {'period': 2, 'armcd': 'PLACEBO', 'epoch': 'PERIOD 2',
                     'start_day': 44, 'end_day': 86, 'washout_days_before': 2},
                    {'period': 3, 'armcd': 'KVD900_300MG', 'epoch': 'PERIOD 3',
                     'start_day': 88, 'end_day': 130, 'washout_days_before': 2},
                ]
            },
            {
                'seqcd': 'BAC',
                'label': 'Sequence BAC: 300mg then 600mg then Placebo',
                'periods': [
                    {'period': 1, 'armcd': 'KVD900_300MG', 'epoch': 'PERIOD 1',
                     'start_day': 1, 'end_day': 42, 'washout_days_before': 0},
                    {'period': 2, 'armcd': 'KVD900_600MG', 'epoch': 'PERIOD 2',
                     'start_day': 44, 'end_day': 86, 'washout_days_before': 2},
                    {'period': 3, 'armcd': 'PLACEBO', 'epoch': 'PERIOD 3',
                     'start_day': 88, 'end_day': 130, 'washout_days_before': 2},
                ]
            },
            {
                'seqcd': 'BCA',
                'label': 'Sequence BCA: 300mg then Placebo then 600mg',
                'periods': [
                    {'period': 1, 'armcd': 'KVD900_300MG', 'epoch': 'PERIOD 1',
                     'start_day': 1, 'end_day': 42, 'washout_days_before': 0},
                    {'period': 2, 'armcd': 'PLACEBO', 'epoch': 'PERIOD 2',
                     'start_day': 44, 'end_day': 86, 'washout_days_before': 2},
                    {'period': 3, 'armcd': 'KVD900_600MG', 'epoch': 'PERIOD 3',
                     'start_day': 88, 'end_day': 130, 'washout_days_before': 2},
                ]
            },
            {
                'seqcd': 'CAB',
                'label': 'Sequence CAB: Placebo then 600mg then 300mg',
                'periods': [
                    {'period': 1, 'armcd': 'PLACEBO', 'epoch': 'PERIOD 1',
                     'start_day': 1, 'end_day': 42, 'washout_days_before': 0},
                    {'period': 2, 'armcd': 'KVD900_600MG', 'epoch': 'PERIOD 2',
                     'start_day': 44, 'end_day': 86, 'washout_days_before': 2},
                    {'period': 3, 'armcd': 'KVD900_300MG', 'epoch': 'PERIOD 3',
                     'start_day': 88, 'end_day': 130, 'washout_days_before': 2},
                ]
            },
            {
                'seqcd': 'CBA',
                'label': 'Sequence CBA: Placebo then 300mg then 600mg',
                'periods': [
                    {'period': 1, 'armcd': 'PLACEBO', 'epoch': 'PERIOD 1',
                     'start_day': 1, 'end_day': 42, 'washout_days_before': 0},
                    {'period': 2, 'armcd': 'KVD900_300MG', 'epoch': 'PERIOD 2',
                     'start_day': 44, 'end_day': 86, 'washout_days_before': 2},
                    {'period': 3, 'armcd': 'KVD900_600MG', 'epoch': 'PERIOD 3',
                     'start_day': 88, 'end_day': 130, 'washout_days_before': 2},
                ]
            },
        ],
        
        'visits': [
            {'name': 'SCREENING', 'day': -28, 'window_before': 0, 'window_after': 14},
            {'name': 'RANDOMIZATION', 'day': 1, 'window_before': 0, 'window_after': 0},
            {'name': 'POST-ATTACK 1 TELEVISIT', 'day': 45, 'window_before': 14, 'window_after': 14},
            {'name': 'POST-ATTACK 2 TELEVISIT', 'day': 90, 'window_before': 14, 'window_after': 14},
            {'name': 'POST-ATTACK 3 TELEVISIT', 'day': 135, 'window_before': 14, 'window_after': 14},
            {'name': 'FINAL VISIT', 'day': 175, 'window_before': 14, 'window_after': 14},
        ],
        
        'demographics': {
            'age_min': 12,
            'age_max': 75,
            'age_mean': 38,
            'age_sd': 14,
            'total_subjects': 90,
            'subjects_per_arm': {
                'ABC': 15, 'ACB': 15, 'BAC': 15,
                'BCA': 15, 'CAB': 15, 'CBA': 15,
            },
            'sex_distribution': {'M': 0.40, 'F': 0.60},
            'race_distribution': {
                'WHITE': 0.75, 'BLACK OR AFRICAN AMERICAN': 0.08,
                'ASIAN': 0.10, 'OTHER': 0.07
            },
            'country': 'USA',
            'sites': ['SITE' + str(i).zfill(3) for i in range(1, 21)],
            'screen_fail_rate': 0.10,
        },
        
        'total_study_days': 175,
        'treatment_duration_weeks': 19,
        'follow_up_weeks': 6,
    },
}


def get_protocol_spec(protocol_name: str) -> Optional[Dict[str, Any]]:
    """
    Get specification for a known protocol.
    
    Args:
        protocol_name: Short name (e.g., 'tj301', 'protect', 'bendita')
        
    Returns:
        Protocol specification dictionary or None if not found
    """
    return KNOWN_PROTOCOLS.get(protocol_name.lower())


def list_available_protocols() -> List[str]:
    """Return list of available protocol names."""
    return list(KNOWN_PROTOCOLS.keys())


def detect_protocol_from_text(text: str) -> Optional[str]:
    """
    Attempt to identify a known protocol from text.
    
    Args:
        text: Protocol text to analyze
        
    Returns:
        Protocol name if detected, None otherwise
    """
    text_lower = text.lower()
    
    detection_patterns = {
        'tj301': ['tj301', 'olamkicept', 'ctj301', 'ulcerative colitis'],
        'protect': ['teplizumab', 'prv-031', 'type 1 diabetes', 't1d'],
        'sutimlimab': ['sutimlimab', 'bivv009', 'cold agglutinin'],
        'bendita': ['bendita', 'benznidazole', 'chagas'],
        'hs11421': ['hs-11-421', 'secukinumab', 'psoriatic arthritis'],
        'herald': ['herald', 'cv-ncov', 'ad26.cov2', 'covid-19 vaccine'],
        'bda': ['bda', 'av005', 'tyree', 'budesonide/albuterol', 'pt027', 'exercise-induced bronchoconstriction'],
        'usl261': ['usl261', 'p261-402', 'artemis', 'intranasal midazolam', 'seizure cluster'],
        'konfident': ['konfident', 'kvd900', 'kvd900-301', 'hereditary angioedema', 'kalvista'],
    }
    
    for proto_name, patterns in detection_patterns.items():
        if any(p in text_lower for p in patterns):
            return proto_name
    
    return None
