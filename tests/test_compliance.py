import os
import time

from src.compliance import (
    AuditGenerator,
    ConsentTracker,
    ExportController,
    RetentionEnforcer,
    scrub_bio,
    scrub_emails,
    scrub_phone_numbers,
    scrub_tracking_links,
)


def test_scrub_emails():
    """Test email scrubbing regex."""
    assert scrub_emails("Contact me at test@example.com!") == "Contact me at [EMAIL_REMOVED]!"
    assert (
        scrub_emails("emails: a@b.co and test.name+123@domain.org")
        == "emails: [EMAIL_REMOVED] and [EMAIL_REMOVED]"
    )
    assert scrub_emails("No email here") == "No email here"


def test_scrub_phone_numbers():
    """Test phone number scrubbing regex."""
    assert scrub_phone_numbers("Call +1 555-123-4567") == "Call [PHONE_REMOVED]"
    assert scrub_phone_numbers("Mobile: (555) 123 4567") == "Mobile: [PHONE_REMOVED]"
    assert scrub_phone_numbers("EU format: +44 20 7123 1234") == "EU format: [PHONE_REMOVED]"
    # Should not scrub standard small numbers
    assert scrub_phone_numbers("I have 10 apples") == "I have 10 apples"
    assert scrub_phone_numbers("Price is $1,000") == "Price is $1,000"


def test_scrub_tracking_links():
    """Test URL and tracking link scrubbing regex."""
    assert (
        scrub_tracking_links("Check my site: https://example.com")
        == "Check my site: [LINK_REMOVED]"
    )
    assert scrub_tracking_links("Or www.test.org") == "Or [LINK_REMOVED]"
    assert scrub_tracking_links("Linktree: linktr.ee/myprofile") == "Linktree: [LINK_REMOVED]"
    assert scrub_tracking_links("Hello world") == "Hello world"


def test_scrub_bio():
    """Test full orchestration of bio scrubbing."""
    messy_bio = (
        "Welcome to my page! \n"
        "Business: inquiries@test.com \n"
        "WhatsApp: +1-555-987-6543 \n"
        "Store: my-store.com/shop"
    )

    cleaned = scrub_bio(messy_bio)

    assert "[EMAIL_REMOVED]" in cleaned
    assert "[PHONE_REMOVED]" in cleaned
    assert "[LINK_REMOVED]" in cleaned
    assert "Welcome to my page!" in cleaned

    # Test None safety
    assert scrub_bio(None) is None
    assert scrub_bio("") == ""


def test_consent_tracker():
    """Test ConsentTracker logic."""
    tracker = ConsentTracker(require_consent=True)
    assert tracker.check_consent("user1", True) is True
    assert tracker.check_consent("user2", False) is False

    tracker_no_req = ConsentTracker(require_consent=False)
    assert tracker_no_req.check_consent("user3", False) is True


def test_retention_enforcer(tmp_path):
    """Test RetentionEnforcer logic using temporary files."""
    enforcer = RetentionEnforcer(max_days=7)

    # Create an old file (10 days old)
    old_file = tmp_path / "old.json"
    old_file.write_text("{}")
    old_time = time.time() - (10 * 86400)
    os.utime(old_file, (old_time, old_time))

    # Create a new file (1 day old)
    new_file = tmp_path / "new.json"
    new_file.write_text("{}")
    new_time = time.time() - (1 * 86400)
    os.utime(new_file, (new_time, new_time))

    # Enforce
    deleted = enforcer.enforce_retention(str(tmp_path))

    assert deleted == 1
    assert not old_file.exists()
    assert new_file.exists()

    # Non-existent dir returns 0
    assert enforcer.enforce_retention("/does/not/exist") == 0


def test_export_controller(tmp_path):
    """Test ExportController logic."""
    controller = ExportController()

    safe_csv = tmp_path / "safe.csv"
    safe_csv.write_text("profile_id,followers,following\n123,500,10")
    assert controller.verify_export(str(safe_csv)) is True

    risky_csv = tmp_path / "risky.csv"
    risky_csv.write_text("profile_id,email,followers\n123,test@example.com,500")
    assert controller.verify_export(str(risky_csv)) is False

    assert controller.verify_export("/does/not/exist") is False


def test_audit_generator():
    """Test AuditGenerator logic."""
    generator = AuditGenerator()
    report = generator.generate_report("run_123")

    assert "EduIG-Pipeline Compliance Report" in report
    assert "run_123" in report
    assert "Verified" in report
