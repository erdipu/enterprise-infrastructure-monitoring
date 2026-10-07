#!/usr/bin/env python3
"""
Enterprise Test Runner
Discovers and executes all automated unit and integration tests across the platform.
"""

import unittest
import sys
import os
import time

def run_all_tests():
    test_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(test_dir)
    sys.path.insert(0, os.path.join(project_root, "backend"))
    sys.path.insert(0, test_dir)

    print("=" * 75)
    print(" ENTERPRISE INFRASTRUCTURE MONITORING - AUTOMATED TEST SUITE")
    print("=" * 75)

    loader = unittest.TestLoader()
    suite = loader.discover(start_dir=test_dir, pattern="test_*.py")

    start_time = time.time()
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    elapsed = round(time.time() - start_time, 3)

    print("\n" + "=" * 75)
    print(" TEST EXECUTION SUMMARY")
    print("=" * 75)
    print(f" Total Tests Run : {result.testsRun}")
    print(f" Tests Passed    : {result.testsRun - len(result.failures) - len(result.errors)}")
    print(f" Tests Failed    : {len(result.failures)}")
    print(f" Tests Errored   : {len(result.errors)}")
    print(f" Elapsed Time    : {elapsed}s")
    print("=" * 75)

    if result.wasSuccessful():
        print(" [✓] ALL PLATFORM TEST SUITES PASSED SUCCESSFULLY!")
        return 0
    else:
        print(" [✗] SOME TESTS FAILED. PLEASE INSPECT LOGS ABOVE.")
        return 1

if __name__ == "__main__":
    sys.exit(run_all_tests())
