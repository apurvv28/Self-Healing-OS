"""Tests for KernelPatchDatabase module."""

from remediation.kernel_db import KernelPatchDatabase


def test_kernel_db_match_approved_remediation():
    db = KernelPatchDatabase(config_path="config/kernel-remediations.yaml")

    evidence = "Resetting chip after gpu lockup on card 0"
    match = db.find_remediation_for_evidence(evidence)

    assert match is not None
    assert match["signature_id"] == "gpu_hang_i915"
    assert match["approved_action"] == "reload_driver"
    assert match["target"] == "i915"
    assert match["admin_approved"] is True


def test_kernel_db_unapproved_remediation():
    db = KernelPatchDatabase(config_path="config/kernel-remediations.yaml")

    evidence = "unable to handle kernel NULL pointer dereference at 0x000"
    match = db.find_remediation_for_evidence(evidence)

    assert match is not None
    assert match["signature_id"] == "kernel_null_pointer_patch"
    assert match["admin_approved"] is False
