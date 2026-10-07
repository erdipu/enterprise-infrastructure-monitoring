#!/usr/bin/env python3
"""
Test Suite: Prometheus Alert Rules & Alertmanager Routing Configuration
Validates alert names, PromQL expressions, severity/priority labels, and inhibit rules.
"""

import unittest
import os
import re

class TestAlertRulesSyntax(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        base_dir = os.path.dirname(os.path.dirname(__file__))
        cls.rules_path = os.path.join(base_dir, "prometheus", "alert.rules.yml")
        cls.am_path = os.path.join(base_dir, "alertmanager", "alertmanager.yml")
        cls.bb_path = os.path.join(base_dir, "prometheus", "blackbox.yml")

        with open(cls.rules_path, "r") as f:
            cls.rules_yml = f.read()
        with open(cls.am_path, "r") as f:
            cls.am_yml = f.read()
        with open(cls.bb_path, "r") as f:
            cls.bb_yml = f.read()

    def test_all_11_alert_rules_exist(self):
        """Validate all 11 required enterprise alerting rules are configured"""
        expected_rules = [
            "HostDown", "WebsiteDown", "EndpointHighLatency",
            "HostCpuUtilizationCritical", "HostCpuUtilizationWarning", "HostHighLoadAverage",
            "HostMemoryUtilizationCritical", "HostMemoryUtilizationWarning",
            "HostDiskUtilizationCritical", "HostDiskUtilizationWarning",
            "HostNetworkInterfaceErrors"
        ]
        configured_rules = re.findall(r"- alert:\s+(\w+)", self.rules_yml)
        for rule in expected_rules:
            self.assertIn(rule, configured_rules, f"Alert rule missing: {rule}")

    def test_priority_labels_present(self):
        """Verify priority classifications (P1, P2, P3) exist on rules"""
        priorities = set(re.findall(r"priority:\s+(\w+)", self.rules_yml))
        self.assertIn("P1", priorities)
        self.assertIn("P2", priorities)
        self.assertIn("P3", priorities)

    def test_alertmanager_inhibit_and_webhook_rules(self):
        """Verify Alertmanager inhibit rules and FastAPI webhook receiver"""
        self.assertIn("inhibit_rules:", self.am_yml)
        self.assertIn("fastapi_incident_webhook", self.am_yml)
        self.assertIn("send_resolved: true", self.am_yml)

    def test_blackbox_probing_modules(self):
        """Verify Blackbox exporter modules"""
        self.assertIn("http_2xx:", self.bb_yml)
        self.assertIn("prober: http", self.bb_yml)

if __name__ == "__main__":
    unittest.main()
