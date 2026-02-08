#!/usr/bin/env python3
"""
AERIS Experiment Runner

Convenient wrapper to run various experiments and tests for the AERIS protocol.

Usage:
    python scripts/run_experiments.py --test comprehensive
    python scripts/run_experiments.py --test comparison
    python scripts/run_experiments.py --test quick
"""

import sys
import os
import argparse
import subprocess
from pathlib import Path

# Add src directory to Python path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

def run_comprehensive_test():
    """Run comprehensive multi-scale network testing (AERIS unified)"""
    print("🔬 Running Comprehensive AERIS Testing (Unified)...")
    print("=" * 60)

    # Use the integrated AERIS test as the comprehensive entry
    cmd = [sys.executable, "tests/test_aeris_integration.py"]
    result = subprocess.run(cmd, cwd=Path(__file__).parent.parent)

    if result.returncode == 0:
        print("✅ Comprehensive test completed successfully!")
    else:
        print("❌ Comprehensive test failed!")

    return result.returncode

def run_comparison_test():
    """Run baseline protocol comparison (AERIS vs classics)"""
    print("📊 Running Baseline Protocol Comparison (AERIS vs LEACH/PEGASIS/HEED)...")
    print("=" * 60)

    # Use integrated AERIS comparison test script
    cmd = [sys.executable, "tests/test_aeris_integration.py"]
    result = subprocess.run(cmd, cwd=Path(__file__).parent.parent)

    if result.returncode == 0:
        print("✅ Comparison test completed successfully!")
    else:
        print("❌ Comparison test failed!")

    return result.returncode

def run_quick_test():
    """Run quick validation test"""
    print("⚡ Running Quick Validation Test...")
    print("=" * 60)
    
    cmd = [sys.executable, "tests/simple_aeris_smoke_test.py"]
    result = subprocess.run(cmd, cwd=Path(__file__).parent.parent)
    
    if result.returncode == 0:
        print("✅ Quick test completed successfully!")
    else:
        print("❌ Quick test failed!")
    
    return result.returncode

def run_all_tests():
    """Run all available tests"""
    print("🚀 Running All AERIS Tests...")
    print("=" * 60)
    
    tests = [
        ("Quick Test", run_quick_test),
        ("Comparison Test", run_comparison_test),
        ("Comprehensive Test", run_comprehensive_test)
    ]
    
    results = []
    for test_name, test_func in tests:
        print(f"\n📋 Starting {test_name}...")
        result = test_func()
        results.append((test_name, result))
        print(f"{'✅' if result == 0 else '❌'} {test_name} {'passed' if result == 0 else 'failed'}")
    
    print("\n" + "=" * 60)
    print("📊 Test Summary:")
    for test_name, result in results:
        status = "PASSED" if result == 0 else "FAILED"
        print(f"  {test_name}: {status}")
    
    failed_tests = [name for name, result in results if result != 0]
    if failed_tests:
        print(f"\n❌ {len(failed_tests)} test(s) failed: {', '.join(failed_tests)}")
        return 1
    else:
        print(f"\n🎉 All {len(results)} tests passed successfully!")
        return 0

def main():
    parser = argparse.ArgumentParser(
        description="AERIS Experiment Runner",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python scripts/run_experiments.py --test quick
  python scripts/run_experiments.py --test comparison  
  python scripts/run_experiments.py --test comprehensive
  python scripts/run_experiments.py --test all
        """
    )
    
    parser.add_argument(
        "--test", "-t",
        choices=["quick", "comparison", "comprehensive", "all"],
        default="quick",
        help="Type of test to run (default: quick)"
    )
    
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Enable verbose output"
    )
    
    args = parser.parse_args()
    
    # Change to project root directory
    os.chdir(Path(__file__).parent.parent)
    
    print("🚀 AERIS Protocol Experiment Runner")
    print(f"📁 Working directory: {os.getcwd()}")
    print(f"🔬 Test type: {args.test}")
    print()
    
    # Run selected test
    if args.test == "quick":
        return run_quick_test()
    elif args.test == "comparison":
        return run_comparison_test()
    elif args.test == "comprehensive":
        return run_comprehensive_test()
    elif args.test == "all":
        return run_all_tests()
    else:
        print(f"❌ Unknown test type: {args.test}")
        return 1

if __name__ == "__main__":
    sys.exit(main())
