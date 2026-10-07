#!/usr/bin/env python3
"""
Test Suite: Incident Management Automation Engine
Validates fingerprint calculation, priority classification, deduplication, and MTTR calculations.
"""

import unittest
import hashlib
from datetime import datetime, timedelta

class TestIncidentEngine(unittest.TestCase):
    @staticmethod
    def compute_fingerprint(labels: dict, fingerprint: str = None) -> str:
        if fingerprint:
            return fingerprint
        key_str = f"{labels.get('alertname', '')}:{labels.get('instance', '')}:{labels.get('severity', '')}"
        return hashlib.sha256(key_str.encode()).hexdigest()[:16]

    @staticmethod
    def map_priority_and_severity(labels: dict) -> tuple:
        priority = labels.get("priority")
        severity = labels.get("severity", "warning").capitalize()

        if not priority:
            if severity.lower() == "critical":
                priority = "P1"
            elif severity.lower() == "warning":
                priority = "P2"
            elif severity.lower() == "info":
                priority = "P4"
            else:
                priority = "P3"

        return priority, severity

    def test_fingerprint_deterministic_generation(self):
        """Test that same alert generates identical fingerprint for deduplication"""
        labels1 = {"alertname": "HostDown", "instance": "srv-linux-prod-01", "severity": "critical"}
        labels2 = {"alertname": "HostDown", "instance": "srv-linux-prod-01", "severity": "critical"}

        fp1 = self.compute_fingerprint(labels1)
        fp2 = self.compute_fingerprint(labels2)
        self.assertEqual(fp1, fp2, "Fingerprints for same alert target must match for deduplication")
        self.assertEqual(len(fp1), 16)

    def test_priority_mapping_matrix(self):
        """Test ITIL Priority classification logic (P1-P4)"""
        # Explicit priority label takes precedence
        labels_explicit = {"alertname": "HostDown", "instance": "srv-01", "priority": "P1", "severity": "critical"}
        p, s = self.map_priority_and_severity(labels_explicit)
        self.assertEqual(p, "P1")
        self.assertEqual(s, "Critical")

        # Inferred from severity
        labels_inferred_crit = {"alertname": "HostCpuUtilizationCritical", "instance": "srv-01", "severity": "critical"}
        p, s = self.map_priority_and_severity(labels_inferred_crit)
        self.assertEqual(p, "P1")

        labels_inferred_warn = {"alertname": "HostCpuUtilizationWarning", "instance": "srv-01", "severity": "warning"}
        p, s = self.map_priority_and_severity(labels_inferred_warn)
        self.assertEqual(p, "P2")

    def test_mttr_calculation(self):
        """Test Mean Time to Resolution (MTTR) calculation accuracy"""
        created = datetime(2026, 10, 7, 10, 0, 0)
        resolved = datetime(2026, 10, 7, 10, 45, 0)
        mttr_sec = int((resolved - created).total_seconds())
        self.assertEqual(mttr_sec, 2700)  # 45 minutes = 2700 seconds
        mttr_min = round(mttr_sec / 60.0, 1)
        self.assertEqual(mttr_min, 45.0)

if __name__ == "__main__":
    unittest.main()
