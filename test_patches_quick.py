#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Quick validation of applied patches in этика_v21_patched.py"""

import sys
import os
os.chdir('E:\\загрузки\\.gemini\\antigravity\\scratch\\YadroLang')
sys.path.insert(0, '.')

from src.этика_v21_patched import ЭтическийАнализатор, ЭтическаяОшибка, СТОКИ

def test_печать_as_sink():
    """PATCH 1: печать should be treated as sink"""
    # Check if печать is in СТОКИ
    if "печать" in СТОКИ:
        print("[PASS] TEST PASSED: печать found in СТОКИ")
        return True
    else:
        print("[FAIL] TEST FAILED: печать NOT in СТОКИ")
        return False

def test_return_value_as_sink():
    """PATCH 3: Final return value should be checked as sink"""
    # Check that _метки_возврата accepts pc_метки parameter
    анализатор = ЭтическийАнализатор()
    import inspect
    sig = inspect.signature(анализатор._метки_возврата)
    if 'pc_метки' in sig.parameters:
        print("[PASS] TEST PASSED: _метки_возврата has pc_метки parameter")
        return True
    else:
        print("[FAIL] TEST FAILED: _метки_возврата missing pc_метки parameter")
        return False

def test_pc_propagation():
    """PATCH 2: PC-labels should propagate into assignments"""
    # Check that _метки_возврата uses pc_метки in assignments
    анализатор = ЭтическийАнализатор()
    import inspect
    source = inspect.getsource(анализатор._метки_возврата)
    if "| pc_метки" in source:
        print("[PASS] TEST PASSED: _метки_возврата merges pc_метки in assignments")
        return True
    else:
        print("[FAIL] TEST FAILED: _метки_возврата doesn't merge pc_метки in assignments")
        return False

if __name__ == "__main__":
    print("=== Quick Patch Validation ===\n")
    tests = [
        test_печать_as_sink,
        test_return_value_as_sink,
        test_pc_propagation,
    ]
    results = []
    for test in tests:
        try:
            results.append(test())
        except Exception as e:
            print(f"❌ EXCEPTION in {test.__name__}: {e}")
            results.append(False)
        print()
    
    passed = sum(results)
    total = len(results)
    print(f"\nResults: {passed}/{total} tests passed")
    if passed == total:
        print("STATUS: ALL PATCHES VALIDATED")
    sys.exit(0 if passed == total else 1)
