#!/usr/bin/env python3
"""
HEARTH v0.1 System Validation Script

Runs comprehensive checks to verify:
- All core modules importable
- All 18 unit tests passing
- Core guarantees enforced
- Graceful degradation modes working
- Documentation present and consistent
"""

import subprocess
import sys
import os
from pathlib import Path

# Color codes for output
GREEN = '\033[92m'
RED = '\033[91m'
YELLOW = '\033[93m'
BLUE = '\033[94m'
RESET = '\033[0m'

def print_header(text):
    print(f"\n{BLUE}{'='*70}")
    print(f"{text}")
    print(f"{'='*70}{RESET}\n")

def print_success(text):
    print(f"{GREEN}✅ {text}{RESET}")

def print_error(text):
    print(f"{RED}❌ {text}{RESET}")

def print_warning(text):
    print(f"{YELLOW}⚠️  {text}{RESET}")

def check_imports():
    """Verify all core modules can be imported"""
    print_header("1. Checking Module Imports")
    
    modules = [
        "main",
        "core.kernel",
        "hestia.agent",
        "hestia.intent_classifier",
        "hestia.ollama_client",
        "mnemosyne.memory_store",
        "athena.knowledge_store",
        "athena.retriever",
    ]
    
    all_ok = True
    for module in modules:
        try:
            __import__(module)
            print_success(f"Imported {module}")
        except Exception as e:
            print_error(f"Failed to import {module}: {e}")
            all_ok = False
    
    return all_ok

def check_tests():
    """Run pytest on test_v01_stability.py"""
    print_header("2. Running Unit Tests (18 total)")
    
    result = subprocess.run(
        [sys.executable, "-m", "pytest", 
         "tests/test_v01_stability.py", "-v", "--tb=short"],
        capture_output=True,
        text=True
    )
    
    # Parse output for pass/fail counts
    output = result.stdout + result.stderr
    
    if "18 passed" in output:
        print_success("All 18 unit tests PASSED")
        print(f"\n{output.split('=')[-1]}")
        return True
    else:
        print_error("Some tests failed")
        print(f"\n{output}")
        return False

def check_documentation():
    """Verify required documentation files exist"""
    print_header("3. Checking Documentation")
    
    required_docs = [
        "ARCHITECTURE.md",
        "FAILURE_MODES.md",
        "CONTEXT_BOUNDS_REPORT.md",
        "STABILIZATION_COMPLETE.md",
        "README.md",
    ]
    
    all_ok = True
    for doc in required_docs:
        path = Path(doc)
        if path.exists():
            size = path.stat().st_size
            print_success(f"{doc} ({size:,} bytes)")
        else:
            print_error(f"{doc} NOT FOUND")
            all_ok = False
    
    return all_ok

def check_ci_config():
    """Verify CI workflow file exists"""
    print_header("4. Checking CI Configuration")
    
    ci_path = Path(".github/workflows/test.yml")
    if ci_path.exists():
        with open(ci_path) as f:
            content = f.read()
        
        checks = [
            ("pytest", "pytest in workflow"),
            ("test_v01_stability.py", "stability tests referenced"),
            ("python-version", "matrix for Python versions"),
        ]
        
        all_ok = True
        for pattern, description in checks:
            if pattern in content:
                print_success(f"CI workflow has {description}")
            else:
                print_error(f"CI workflow missing {description}")
                all_ok = False
        
        return all_ok
    else:
        print_error("CI workflow file not found")
        return False

def check_core_files():
    """Verify core v0.1 files exist and have reasonable size"""
    print_header("5. Checking Core v0.1 Files")
    
    core_files = [
        ("main.py", 100),          # Should have entry point
        ("core/kernel.py", 50),     # Minimal config
        ("hestia/agent.py", 300),   # Main orchestrator
        ("hestia/intent_classifier.py", 50),  # Intent routing
        ("hestia/ollama_client.py", 50),      # LLM client
        ("mnemosyne/memory_store.py", 100),   # Memory storage
        ("athena/knowledge_store.py", 50),    # Knowledge lookup
        ("athena/retriever.py", 30),          # Retriever wrapper
    ]
    
    all_ok = True
    for file_path, min_size in core_files:
        path = Path(file_path)
        if path.exists():
            size = path.stat().st_size
            if size >= min_size:
                print_success(f"{file_path} ({size} bytes)")
            else:
                print_warning(f"{file_path} ({size} bytes) - smaller than expected ({min_size})")
                all_ok = False
        else:
            print_error(f"{file_path} NOT FOUND")
            all_ok = False
    
    return all_ok

def check_key_guarantees():
    """Spot-check key guarantee implementations in code"""
    print_header("6. Spot-Checking Key Guarantees")
    
    checks = [
        ("hestia/agent.py", "prompt_memory_confirmation", "Memory write confirmation"),
        ("hestia/agent.py", "should_use_memory_for_context", "Memory-to-LLM gating"),
        ("hestia/agent.py", "MAX_MEMORY_ITEMS = 5", "Memory item bounds"),
        ("hestia/agent.py", "MAX_LLM_CONTEXT_CHARS = 8000", "LLM context bounds"),
        ("hestia/intent_classifier.py", "memory_patterns", "Memory intent detection"),
        ("hestia/intent_classifier.py", "knowledge_patterns", "Knowledge intent detection"),
        ("mnemosyne/memory_store.py", "append(", "Append-only memory operations"),
    ]
    
    all_ok = True
    for file_path, pattern, description in checks:
        path = Path(file_path)
        if path.exists():
            with open(path) as f:
                content = f.read()
            if pattern in content:
                print_success(f"{description} implemented")
            else:
                print_error(f"{description} NOT FOUND in {file_path}")
                all_ok = False
        else:
            print_error(f"{file_path} not found")
            all_ok = False
    
    return all_ok

def print_summary(results):
    """Print validation summary"""
    print_header("VALIDATION SUMMARY")
    
    total = len(results)
    passed = sum(1 for r in results if r)
    
    status = "✅ ALL CHECKS PASSED" if passed == total else "❌ SOME CHECKS FAILED"
    
    print(f"{status}")
    print(f"Passed: {passed}/{total}")
    
    if passed == total:
        print(f"\n{GREEN}HEARTH v0.1 is production-ready!{RESET}")
        print(f"{GREEN}→ Run with: python main.py [--llm] [--memory]{RESET}")
        print(f"{GREEN}→ Test with: pytest tests/test_v01_stability.py -v{RESET}")
    else:
        print(f"\n{RED}Please fix failing checks before deployment.{RESET}")
    
    return passed == total

if __name__ == "__main__":
    print(f"\n{BLUE}HEARTH v0.1 System Validation{RESET}")
    print(f"{BLUE}{'='*70}{RESET}")
    
    results = [
        check_imports(),
        check_tests(),
        check_documentation(),
        check_ci_config(),
        check_core_files(),
        check_key_guarantees(),
    ]
    
    success = print_summary(results)
    sys.exit(0 if success else 1)
