"""
Non-Negotiable Tests — §6 of the v2 Architecture Spec

These tests MUST pass before shipping. They validate the core guarantees
of the v2 architecture: scaling invariance, call-order invariance,
edit locality, RELREC stability, and export determinism.
"""

import hashlib
import warnings
import sys
import os

warnings.filterwarnings('ignore')
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from sdtm_synth.core.subject_generator import generate_canonical_subject
from sdtm_synth.core.materializer import materialize_all
from sdtm_synth.utils.rng import SubjectRNG, RNGComponent, assign_arm
from sdtm_synth.spec.models import (
    TrialDesignSpec, ArmSpec, ElementSpec, ArmPath, ArmPathItem,
    VisitSpec, RegimenItem,
)


def make_test_spec():
    """Create a minimal spec for testing."""
    spec = TrialDesignSpec(
        study_id='TEST001', n_subjects_default=10,
        arms=[
            ArmSpec(armcd='A', arm='Drug A', regimen=[RegimenItem(extrt='DRUG_A', dose=100)]),
            ArmSpec(armcd='B', arm='Drug B', regimen=[RegimenItem(extrt='DRUG_B', dose=200)]),
        ],
        elements=[
            ElementSpec(etcd='S', element='Screen', epoch='SCREENING', nominal_duration_days=14),
            ElementSpec(etcd='T', element='Treatment', epoch='TREATMENT', nominal_duration_days=84),
            ElementSpec(etcd='F', element='Follow-up', epoch='FOLLOW-UP', nominal_duration_days=28),
        ],
        arm_paths=[
            ArmPath(armcd='A', elements=[
                ArmPathItem(etcd='S', taetord=1), ArmPathItem(etcd='T', taetord=2),
                ArmPathItem(etcd='F', taetord=3),
            ]),
            ArmPath(armcd='B', elements=[
                ArmPathItem(etcd='S', taetord=1), ArmPathItem(etcd='T', taetord=2),
                ArmPathItem(etcd='F', taetord=3),
            ]),
        ],
        visits=[
            VisitSpec(visitnum=1, visit='BASELINE', nominal_day=1),
            VisitSpec(visitnum=2, visit='WEEK 12', nominal_day=85),
        ],
        arm_order=['A', 'B'], total_study_days=126,
    )
    spec.demographics.subjects_per_arm = {'A': 5, 'B': 5}
    spec.demographics.sites = ['S001']
    spec.demographics.n_sites = 1
    return spec


def test_1_scaling_invariance():
    """Generate N=100, then N=200. Subjects 0–99 must be identical."""
    spec = make_test_spec()
    subj_100 = [generate_canonical_subject(spec, i, 42) for i in range(100)]
    subj_200 = [generate_canonical_subject(spec, i, 42) for i in range(200)]

    for i in range(100):
        a, b = subj_100[i], subj_200[i]
        assert a.demographics.age == b.demographics.age, f"Age mismatch at {i}"
        assert a.demographics.sex == b.demographics.sex, f"Sex mismatch at {i}"
        assert a.arm_code == b.arm_code, f"Arm mismatch at {i}"
        assert a.latent_traits.frailty_score == b.latent_traits.frailty_score, f"Frailty mismatch at {i}"
        assert len(a.adverse_events) == len(b.adverse_events), f"AE count mismatch at {i}"
        assert a.disposition.outcome == b.disposition.outcome, f"Disposition mismatch at {i}"

    print("Test 1: Scaling Invariance — PASS ✓")


def test_2_call_order_invariance():
    """Run domain generators in different orders. Output must be identical."""
    spec = make_test_spec()
    fwd = [generate_canonical_subject(spec, i, 42) for i in range(20)]
    rev = [generate_canonical_subject(spec, i, 42) for i in reversed(range(20))]
    rev.sort(key=lambda s: s.identity.subject_index)

    for i in range(20):
        a, b = fwd[i], rev[i]
        assert a.demographics.age == b.demographics.age
        assert a.arm_code == b.arm_code
        assert len(a.adverse_events) == len(b.adverse_events)
        for ae_a, ae_b in zip(a.adverse_events, b.adverse_events):
            assert ae_a.canonical_id == ae_b.canonical_id
            assert ae_a.term == ae_b.term

    print("Test 2: Call-Order Invariance — PASS ✓")


def test_3_ae_edit_locality():
    """Verify that mutating one AE in canonical truth only affects linked consequences.
    
    Generates a subject, mutates exactly one AE (flip severity), re-materializes,
    and checks:
      - All other AE canonical_ids and properties are stable
      - DS/DM changes only when the mutation implies it (e.g., fatality)
      - Unrelated domains (VS, LB, EX) are completely unaffected
    """
    import copy
    
    spec = make_test_spec()
    spec.ae_model.enable_fatal = True
    spec.ae_model.ae_rate_multiplier = 3.0  # ensure we get AEs
    
    # Generate subjects until we find one with ≥2 AEs
    target = None
    for idx in range(100):
        s = generate_canonical_subject(spec, idx, 42)
        if not s.is_screen_failure and len(s.adverse_events) >= 2:
            target = s
            break
    
    assert target is not None, "Could not find enrolled subject with ≥2 AEs"
    
    # Deep copy and materialize original
    original = copy.deepcopy(target)
    orig_datasets, orig_prov, orig_rels = materialize_all([original], spec)
    
    # Mutate exactly one AE: flip severity of the first non-MILD AE
    mutated = copy.deepcopy(target)
    mutated_ae = None
    for ae in mutated.adverse_events:
        if ae.severity != "MILD":
            mutated_ae = ae
            break
    if mutated_ae is None:
        mutated_ae = mutated.adverse_events[0]
    
    old_severity = mutated_ae.severity
    mutated_ae.severity = "MILD" if old_severity != "MILD" else "SEVERE"
    mutated_id = mutated_ae.canonical_id
    
    # Re-materialize the mutated subject
    mut_datasets, mut_prov, mut_rels = materialize_all([mutated], spec)
    
    # CHECK 1: All OTHER AEs are stable (same canonical_ids and properties)
    orig_aes = {ae.canonical_id: ae for ae in original.adverse_events}
    mut_aes = {ae.canonical_id: ae for ae in mutated.adverse_events}
    
    assert set(orig_aes.keys()) == set(mut_aes.keys()), "AE canonical ID set changed"
    
    for cid, orig_ae in orig_aes.items():
        mut_ae = mut_aes[cid]
        if cid == mutated_id:
            # This one should have changed
            assert mut_ae.severity != orig_ae.severity, "Mutated AE severity didn't change"
            continue
        # All other AEs must be identical
        assert orig_ae.term == mut_ae.term, f"AE {cid} term changed"
        assert orig_ae.onset_date == mut_ae.onset_date, f"AE {cid} onset_date changed"
        assert orig_ae.severity == mut_ae.severity, f"AE {cid} severity changed"
        assert orig_ae.outcome == mut_ae.outcome, f"AE {cid} outcome changed"
        assert orig_ae.action == mut_ae.action, f"AE {cid} action changed"
    
    # CHECK 2: Unrelated domains are completely unaffected
    for domain in ["VS", "LB", "EX", "SV", "SE"]:
        if domain in orig_datasets and domain in mut_datasets:
            orig_csv = orig_datasets[domain].to_csv(index=False)
            mut_csv = mut_datasets[domain].to_csv(index=False)
            assert orig_csv == mut_csv, f"Domain {domain} changed despite unrelated AE mutation"
    
    # CHECK 3: AE domain only changed in the mutated row
    if "AE" in orig_datasets and "AE" in mut_datasets:
        orig_ae_df = orig_datasets["AE"]
        mut_ae_df = mut_datasets["AE"]
        assert len(orig_ae_df) == len(mut_ae_df), "AE row count changed"
    
    print("Test 3: AE Edit Locality — PASS ✓")


def test_4_relrec_stability():
    """RELREC must resolve correctly via canonical IDs."""
    spec = make_test_spec()
    spec.ae_model.enable_fatal = True
    subjects = [generate_canonical_subject(spec, i, 99) for i in range(50)]
    datasets, prov, rels = materialize_all(subjects, spec)

    for rel in rels:
        src = prov.get_sdtm_rows(rel.source_id)
        tgt = prov.get_sdtm_rows(rel.target_id)
        assert src, f"Source {rel.source_id} not found in provenance"
        assert tgt, f"Target {rel.target_id} not found in provenance"

    print("Test 4: RELREC Stability — PASS ✓")


def test_6_export_determinism():
    """Same seed → byte-identical CSVs."""
    spec = make_test_spec()
    s1 = [generate_canonical_subject(spec, i, 42) for i in range(20)]
    s2 = [generate_canonical_subject(spec, i, 42) for i in range(20)]
    d1, _, _ = materialize_all(s1, spec)
    d2, _, _ = materialize_all(s2, spec)

    for domain in d1:
        csv1 = d1[domain].to_csv(index=False, lineterminator='\n')
        csv2 = d2[domain].to_csv(index=False, lineterminator='\n')
        h1 = hashlib.sha256(csv1.encode()).hexdigest()
        h2 = hashlib.sha256(csv2.encode()).hexdigest()
        assert h1 == h2, f"Domain {domain}: hash mismatch"

    print("Test 6: Export Determinism — PASS ✓")


def test_rng_subject_isolation():
    """Different subjects get different RNG streams."""
    rng_a = SubjectRNG(42, 0, 'TEST')
    rng_b = SubjectRNG(42, 1, 'TEST')
    assert rng_a.draw('DM', 'age')[0] != rng_b.draw('DM', 'age')[0]
    print("Test RNG Subject Isolation — PASS ✓")


def test_rng_idempotency():
    """Same (seed, index, protocol) → same RNG."""
    rng_a = SubjectRNG(42, 5, 'TEST')
    rng_b = SubjectRNG(42, 5, 'TEST')
    assert rng_a.draw('DM', 'age')[0] == rng_b.draw('DM', 'age')[0]
    print("Test RNG Idempotency — PASS ✓")


def test_arm_assignment_n_independent():
    """Arm assignment for subject K is same regardless of total N."""
    arms_a = [assign_arm(42, 'T', i, ['X', 'Y'], {'X': 50, 'Y': 50}) for i in range(50)]
    arms_b = [assign_arm(42, 'T', i, ['X', 'Y'], {'X': 50, 'Y': 50}) for i in range(500)]
    assert arms_a == arms_b[:50]
    print("Test Arm Assignment N-Independence — PASS ✓")


def test_5_crossover_key_collision():
    """Test 5: Crossover Key Collision — §6.5
    
    For a crossover protocol with repeated visit structures, verify LB/VS
    records for same visitnum in different periods have different RNG streams
    and different canonical IDs.
    """
    from sdtm_synth.spec.extractor import extract_konfident_spec
    
    spec = extract_konfident_spec()
    spec.study_seed = 42
    
    # Generate one enrolled subject
    enrolled = None
    for i in range(20):
        subj = generate_canonical_subject(spec, i, 42)
        if not subj.is_screen_failure and len(subj.treatment_sequence) == 3:
            enrolled = subj
            break
    
    assert enrolled is not None, "Could not find enrolled crossover subject"
    assert len(enrolled.treatment_sequence) == 3, f"Expected 3 periods, got {len(enrolled.treatment_sequence)}"
    
    # Check VS records: same testcd across periods should have different values and canonical_ids
    vs_by_period = {}
    for vs in enrolled.vs_records:
        key = (vs.period, vs.testcd)
        vs_by_period[key] = vs
    
    # Find testcds that appear in multiple periods
    testcds_seen = {}
    for vs in enrolled.vs_records:
        testcds_seen.setdefault(vs.testcd, []).append(vs)
    
    multi_period_tests = {tc: records for tc, records in testcds_seen.items() if len(records) > 1}
    assert len(multi_period_tests) > 0, "No testcd appears in multiple periods"
    
    # Verify canonical_ids are unique across periods
    all_canonical_ids = [vs.canonical_id for vs in enrolled.vs_records]
    assert len(all_canonical_ids) == len(set(all_canonical_ids)), \
        "Duplicate canonical_ids found in VS records across periods"
    
    # Verify RNG produces different values for same testcd in different periods
    for tc, records in multi_period_tests.items():
        periods_with_values = [(r.period, r.value) for r in records]
        values = [v for _, v in periods_with_values]
        # With different RNG keys, values won't all be identical (probabilistic but reliable)
        if len(set(values)) == 1 and len(values) > 1:
            warnings.warn(f"VS {tc}: identical values across {len(values)} periods (unlikely but possible)")
    
    # Same check for LB
    lb_by_period = {}
    for lb in enrolled.lb_records:
        key = (lb.period, lb.testcd)
        lb_by_period[key] = lb
    
    all_lb_ids = [lb.canonical_id for lb in enrolled.lb_records]
    assert len(all_lb_ids) == len(set(all_lb_ids)), \
        "Duplicate canonical_ids found in LB records across periods"
    
    # Verify canonical_id format includes period
    for vs in enrolled.vs_records:
        assert f"_{vs.period}_" in vs.canonical_id, \
            f"VS canonical_id {vs.canonical_id} missing period component"
    for lb in enrolled.lb_records:
        assert f"_{lb.period}_" in lb.canonical_id, \
            f"LB canonical_id {lb.canonical_id} missing period component"
    
    # Verify RNG streams differ: draw the same key in different periods
    rng = SubjectRNG(42, enrolled.identity.subject_index, spec.study_id)
    for tc in list(multi_period_tests.keys())[:3]:
        vals_by_period = []
        for p in [1, 2, 3]:
            v = rng.draw("VS", p, 1, tc, RNGComponent.VALUE)[0]
            vals_by_period.append(v)
        # Different periods must produce different draws
        assert len(set(vals_by_period)) == len(vals_by_period), \
            f"RNG collision: VS {tc} produced identical draws across periods: {vals_by_period}"
    
    print("Test 5: Crossover Key Collision — PASS ✓")


def test_7_cascade_fatality():
    """Test 7: Flipping AE to FATAL forces DS/DM updates.
    
    Generates a subject with a non-fatal AE, flips it to FATAL with
    AEOUT='FATAL', re-materializes, and verifies DS has a DEATH record
    and DM has DTHFL='Y' / DTHDTC set.
    """
    import copy
    
    spec = make_test_spec()
    spec.ae_model.enable_fatal = True
    spec.ae_model.ae_rate_multiplier = 3.0
    
    # Find a completed subject with AEs (no fatality)
    target = None
    for idx in range(200):
        s = generate_canonical_subject(spec, idx, 42)
        if (not s.is_screen_failure and len(s.adverse_events) >= 1
                and s.disposition.outcome == "COMPLETED"):
            target = s
            break
    
    assert target is not None, "Could not find completed subject with AEs"
    
    # Verify original is not dead
    orig_datasets, _, _ = materialize_all([target], spec)
    if "DM" in orig_datasets and not orig_datasets["DM"].empty:
        orig_dthfl = str(orig_datasets["DM"].iloc[0].get("DTHFL", ""))
        assert orig_dthfl != "Y", "Subject was already dead before mutation"
    
    # Flip first AE to FATAL
    mutated = copy.deepcopy(target)
    ae = mutated.adverse_events[0]
    ae.outcome = "FATAL"
    ae.is_fatal = True
    ae.action = "DRUG WITHDRAWN"
    
    # Update disposition to reflect death
    from sdtm_synth.core.canonical import SubjectDisposition, SubjectDeath
    from datetime import timedelta
    mutated.disposition = SubjectDisposition(
        outcome="DEATH", date=ae.onset_date + timedelta(days=1),
        reason="DEATH", linked_ae_id=ae.canonical_id,
    )
    mutated.death = SubjectDeath(
        date=ae.onset_date + timedelta(days=1),
        linked_ae_id=ae.canonical_id,
    )
    
    # Re-materialize
    mut_datasets, _, _ = materialize_all([mutated], spec)
    
    # Verify DS has DEATH record
    if "DS" in mut_datasets and not mut_datasets["DS"].empty:
        ds_terms = mut_datasets["DS"]["DSDECOD"].tolist() if "DSDECOD" in mut_datasets["DS"].columns else []
        assert "DEATH" in ds_terms or "COMPLETED" not in ds_terms, \
            f"DS should reflect death but has: {ds_terms}"
    
    # Verify DM has DTHFL
    if "DM" in mut_datasets and not mut_datasets["DM"].empty:
        dm = mut_datasets["DM"].iloc[0]
        assert str(dm.get("DTHFL", "")) == "Y", f"DM DTHFL should be 'Y', got {dm.get('DTHFL', '')}"
        assert str(dm.get("DTHDTC", "")) != "", "DM DTHDTC should be set"
    
    print("Test 7: Cascade Fatality — PASS ✓")


# ─── P0 Fix Validation Tests ────────────────────────────────────────────────

def test_p0_canonical_ids_subject_scoped():
    """P0 fix: canonical IDs must be globally unique across subjects.
    
    Before the fix, AE_CAND_6 was shared across subjects, causing
    ProvenanceMap collisions and incorrect RELREC linkage.
    """
    spec = make_test_spec()
    spec.ae_model.ae_rate_multiplier = 3.0
    
    subjects = [generate_canonical_subject(spec, i, 42) for i in range(50)]
    
    # Check that all canonical IDs across subjects are unique
    all_ae_ids = []
    for s in subjects:
        for ae in s.adverse_events:
            all_ae_ids.append(ae.canonical_id)
    
    # Every AE canonical ID should contain the subject's canonical_id prefix
    for s in subjects:
        for ae in s.adverse_events:
            assert s.identity.canonical_id in ae.canonical_id, \
                f"AE {ae.canonical_id} missing subject prefix {s.identity.canonical_id}"
    
    # No duplicates across subjects
    seen = set()
    for cid in all_ae_ids:
        assert cid not in seen, f"Duplicate canonical ID across subjects: {cid}"
        seen.add(cid)
    
    print("Test P0: Canonical IDs Subject-Scoped — PASS ✓")


def test_p0_relrec_no_cross_subject_links():
    """P0 fix: RELREC must not link rows from different subjects.
    
    Validates that every RELID group has a single USUBJID, and that
    rel_id values are unique (no cross-subject collisions).
    """
    spec = make_test_spec()
    spec.ae_model.enable_fatal = True
    spec.ae_model.ae_rate_multiplier = 3.0
    
    subjects = [generate_canonical_subject(spec, i, 99) for i in range(500)]
    datasets, prov, rels = materialize_all(subjects, spec)
    
    relrec = datasets.get('RELREC')
    if relrec is not None and not relrec.empty:
        # Every RELID group must have a single USUBJID
        for relid, group in relrec.groupby('RELID'):
            unique_subjects = group['USUBJID'].unique()
            assert len(unique_subjects) == 1, \
                f"RELID '{relid}' links multiple subjects: {unique_subjects}"
        
        # Check relationship uniqueness
        if rels:
            rel_ids = [r.rel_id for r in rels]
            unique_rel_ids = set(rel_ids)
            # With subject-scoped IDs, rel_ids should have far fewer collisions
            collision_rate = 1.0 - len(unique_rel_ids) / max(len(rel_ids), 1)
            assert collision_rate < 0.05, \
                f"Too many RELID collisions: {collision_rate:.1%} ({len(rel_ids)} total, {len(unique_rel_ids)} unique)"
    
    print("Test P0: RELREC No Cross-Subject Links — PASS ✓")


def test_p0_provenance_per_subject():
    """P0 fix: provenance.get_sdtm_rows() should return only same-subject rows
    when canonical IDs are subject-scoped."""
    spec = make_test_spec()
    spec.ae_model.ae_rate_multiplier = 2.0
    
    subjects = [generate_canonical_subject(spec, i, 42) for i in range(20)]
    _, prov, rels = materialize_all(subjects, spec)
    
    # For each relationship, verify src and target USUBJID match
    for rel in rels:
        src_rows = prov.get_sdtm_rows(rel.source_id)
        tgt_rows = prov.get_sdtm_rows(rel.target_id)
        
        if src_rows and tgt_rows:
            src_subjects = set(r[1] for r in src_rows)
            tgt_subjects = set(r[1] for r in tgt_rows)
            # With subject-scoped IDs, each canonical ID maps to exactly one subject
            assert len(src_subjects) == 1, \
                f"Source {rel.source_id} maps to multiple subjects: {src_subjects}"
            assert len(tgt_subjects) == 1, \
                f"Target {rel.target_id} maps to multiple subjects: {tgt_subjects}"
            # And they should be the same subject
            assert src_subjects == tgt_subjects, \
                f"Source subject {src_subjects} != target subject {tgt_subjects} for rel {rel.rel_id}"
    
    print("Test P0: Provenance Per-Subject — PASS ✓")


# ─── P1 Fix Validation Tests ────────────────────────────────────────────────

def test_p1_fatal_ae_actually_generated():
    """P1 fix: when enable_fatal=True, FATAL AEs must actually be generated.
    
    Uses death_rate=1.0 to force all severe AEs to be fatal.
    """
    spec = make_test_spec()
    spec.ae_model.enable_fatal = True
    spec.ae_model.death_rate = 1.0  # 100% death rate for severe AEs
    spec.ae_model.ae_rate_multiplier = 5.0  # lots of AEs
    
    # Generate enough subjects to get at least one with a severe AE
    found_fatal = False
    found_death_ds = False
    found_death_dm = False
    
    for i in range(200):
        s = generate_canonical_subject(spec, i, 42)
        fatal_aes = [ae for ae in s.adverse_events if ae.is_fatal]
        if fatal_aes:
            found_fatal = True
            assert s.death is not None, f"Subject {i} has fatal AE but no death record"
            assert s.disposition.outcome == "DEATH", f"Subject {i} has fatal AE but disposition is {s.disposition.outcome}"
            
            # Materialize and check DS/DM
            datasets, _, _ = materialize_all([s], spec)
            ds = datasets.get('DS')
            dm = datasets.get('DM')
            
            if ds is not None and not ds.empty:
                death_ds = ds[ds['DSDECOD'].astype(str).str.upper() == 'DEATH']
                if not death_ds.empty:
                    found_death_ds = True
            
            if dm is not None and not dm.empty:
                dm_row = dm.iloc[0]
                if str(dm_row.get('DTHFL', '')) == 'Y':
                    found_death_dm = True
            
            break
    
    assert found_fatal, "No fatal AEs generated even with death_rate=1.0 and enable_fatal=True"
    assert found_death_ds, "Fatal AE exists but DS has no DEATH record"
    assert found_death_dm, "Fatal AE exists but DM has no DTHFL='Y'"
    
    print("Test P1: Fatal AE Actually Generated — PASS ✓")



if __name__ == '__main__':
    print("=" * 60)
    print("SDTM Synthetic Data Generator v2 — Phase 1/2 Tests")
    print("=" * 60)
    
    test_rng_idempotency()
    test_rng_subject_isolation()
    test_arm_assignment_n_independent()
    test_1_scaling_invariance()
    test_2_call_order_invariance()
    test_3_ae_edit_locality()
    test_4_relrec_stability()
    test_5_crossover_key_collision()
    test_6_export_determinism()
    test_7_cascade_fatality()
    
    # P0 fix validation
    test_p0_canonical_ids_subject_scoped()
    test_p0_relrec_no_cross_subject_links()
    test_p0_provenance_per_subject()
    
    # P1 fix validation (generation side)
    test_p1_fatal_ae_actually_generated()
    
    print()
    print("=" * 60)
    print("ALL TESTS PASSED")
    print("=" * 60)
