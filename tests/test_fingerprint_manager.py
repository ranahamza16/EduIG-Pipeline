import pytest

from src.auth.fingerprint_manager import LOCALES, USER_AGENTS, FingerprintManager


def test_generate_deterministic():
    fm1 = FingerprintManager("test_user_1")
    fp1 = fm1.generate()

    # Should get exactly the same fingerprint if we generate again for the same user
    fm2 = FingerprintManager("test_user_1")
    fp2 = fm2.generate()

    assert fp1 == fp2


def test_generate_different_users():
    fm1 = FingerprintManager("user_alpha")
    fp1 = fm1.generate()

    fm2 = FingerprintManager("user_beta")
    fp2 = fm2.generate()

    # Very high probability these are different
    assert fp1 != fp2


def test_fingerprint_bounds():
    fm = FingerprintManager("bounds_tester")
    fp = fm.generate()

    # Check viewport constraints
    assert 1200 <= fp["viewport"]["width"] <= 1400
    assert 700 <= fp["viewport"]["height"] <= 900

    # Check constants
    assert fp["user_agent"] in USER_AGENTS
    assert fp["locale"] in LOCALES
    assert fp["hardware_concurrency"] in [4, 8, 12, 16]


def test_force_new():
    fm = FingerprintManager("test_user_1")
    fp1 = fm.generate()

    # force_new should generate a new random fingerprint for the same user
    fp2 = fm.generate(force_new=True)
    assert fp1 != fp2


def test_verify_consistency():
    fm = FingerprintManager("test_user_1")
    fp1 = fm.generate()

    assert fm.verify_consistency(fp1) is True

    # Alter something
    fp2 = fp1.copy()
    fp2["viewport"] = {"width": 9999, "height": 9999}
    assert fm.verify_consistency(fp2) is False
