#!/usr/bin/env python3
"""
Simple test runner for the organize functionality.
Run all tests from the project root directory.
"""

import subprocess
import sys
from pathlib import Path

def run_tests():
    """Run the organize route tests."""
    tests_dir = Path(__file__).parent
    project_root = tests_dir.parent
    
    print("🧪 MyAnonamouse Search - Test Runner")
    print("=" * 50)
    print(f"📁 Project root: {project_root}")
    print(f"📁 Tests directory: {tests_dir}")
    print()
    
    # Test 1: Quick test with real data
    print("1️⃣ Running quick test with real data...")
    try:
        result = subprocess.run([
            sys.executable, 
            str(tests_dir / "quick_test_organize.py")
        ], cwd=tests_dir, capture_output=True, text=True)
        
        print("STDOUT:")
        print(result.stdout)
        if result.stderr:
            print("STDERR:")
            print(result.stderr)
        print(f"Exit code: {result.returncode}")
    except Exception as e:
        print(f"❌ Quick test failed to run: {e}")
    
    print("\n" + "=" * 50)
    
    # Test 2: Auto-detect test
    print("2️⃣ Running auto-detect test...")
    try:
        result = subprocess.run([
            sys.executable, 
            str(tests_dir / "test_organize.py"),
            "--auto"
        ], cwd=tests_dir, capture_output=True, text=True)
        
        print("STDOUT:")
        print(result.stdout)
        if result.stderr:
            print("STDERR:")
            print(result.stderr)
        print(f"Exit code: {result.returncode}")
    except Exception as e:
        print(f"❌ Auto-detect test failed to run: {e}")
    
    print("\n" + "=" * 50)
    print("🏁 Test run complete!")

if __name__ == "__main__":
    run_tests()