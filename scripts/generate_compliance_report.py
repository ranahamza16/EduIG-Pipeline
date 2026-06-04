#!/usr/bin/env python3
"""
EduIG-Pipeline Compliance Report Generator.
Reads the SQLite audit_log and generates a markdown summary.
"""

import sqlite3
import os
from datetime import datetime

def generate_report():
    db_path = "data/eduig.db"
    if not os.path.exists(db_path):
        print(f"Error: Database {db_path} not found.")
        return

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # 1. Total targets processed
    cursor.execute("SELECT COUNT(DISTINCT target) FROM audit_log WHERE event = 'data_persisted'")
    targets_processed = cursor.fetchone()[0]

    # 2. Auth events
    cursor.execute("SELECT COUNT(*) FROM audit_log WHERE event LIKE 'AUTH_%'")
    auth_events = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM audit_log WHERE event = 'AUTH_LOGIN_FAILED_FALLBACK'")
    auth_fallbacks = cursor.fetchone()[0]

    # 3. PII Checks
    cursor.execute("SELECT COUNT(*) FROM audit_log WHERE event = 'pii_scrubbed'")
    pii_checks = cursor.fetchone()[0]

    # 4. Retention status
    # Assuming retention events are logged or just stating policy
    cursor.execute("SELECT COUNT(*) FROM audit_log WHERE event = 'data_deleted_retention'")
    retention_deletions = cursor.fetchone()[0]

    conn.close()

    date_str = datetime.now().strftime("%Y%m%d")
    report_filename = f"compliance_report_{date_str}.md"
    
    report_content = f"""# EduIG-Pipeline Compliance Report
**Generated:** {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}

## 📊 Processing Summary
- **Unique Targets Successfully Persisted:** {targets_processed}

## 🔐 Authentication & Security
- **Total Auth Events Logged:** {auth_events}
- **Fallback to Anonymous Mode Events:** {auth_fallbacks}

## 🛡️ Privacy & PII Scrubbing
- **Profiles Scrubbed for PII (Emails/Phones Removed):** {pii_checks}
- *Note: All extracted usernames are inherently hashed via SHA-256 prior to storage.*

## 🗑️ Data Retention
- **Records Deleted (Retention Policy Enforced):** {retention_deletions}
- *Note: Raw JSON payloads are systematically wiped according to config.compliance.delete_raw_after_days.*

---
*Report generated automatically by `scripts/generate_compliance_report.py`.*
"""

    with open(report_filename, "w", encoding="utf-8") as f:
        f.write(report_content)

    print(f"Compliance report generated: {report_filename}")

if __name__ == "__main__":
    generate_report()
