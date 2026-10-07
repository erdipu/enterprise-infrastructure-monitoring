#!/usr/bin/env python3
"""
Test Suite: Database Schema & Relational Integrity
Validates SQL DDL definitions, table constraints, relationships, and default seed data.
"""

import unittest
import re
import os

class TestDatabaseSchema(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.schema_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "database", "schema.sql")
        cls.init_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "database", "init.sql")
        with open(cls.schema_path, "r") as f:
            cls.schema_sql = f.read()
        with open(cls.init_path, "r") as f:
            cls.init_sql = f.read()

    def test_core_tables_exist(self):
        """Verify all 8 enterprise tables are defined in DDL"""
        expected_tables = [
            "users", "servers", "monitoring_targets",
            "alerts", "incidents", "incident_comments",
            "notifications", "audit_logs"
        ]
        created_tables = re.findall(r"CREATE TABLE IF NOT EXISTS\s+(\w+)", self.schema_sql, re.IGNORECASE)
        for t in expected_tables:
            self.assertIn(t, created_tables, f"Missing table in schema: {t}")

    def test_foreign_keys_and_indexes(self):
        """Verify foreign key references and indexing strategy"""
        self.assertIn("REFERENCES alerts(id)", self.schema_sql)
        self.assertIn("REFERENCES users(id)", self.schema_sql)
        self.assertIn("REFERENCES incidents(id)", self.schema_sql)
        self.assertIn("idx_incidents_number", self.schema_sql)
        self.assertIn("idx_alerts_fingerprint", self.schema_sql)

    def test_seed_data_present(self):
        """Verify default administrative users and inventory are seeded in init.sql"""
        self.assertIn("'admin'", self.init_sql)
        self.assertIn("'operator'", self.init_sql)
        self.assertIn("'viewer'", self.init_sql)
        self.assertIn("'srv-linux-prod-01'", self.init_sql)
        self.assertIn("'srv-win-ad-01'", self.init_sql)

if __name__ == "__main__":
    unittest.main()
