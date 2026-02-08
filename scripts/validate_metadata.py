#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Metadata Validation Script
Check if result JSON files comply with .claude/RULES.md specification
"""

import sys
import os
import json
import argparse
from pathlib import Path
from datetime import datetime

# Required top-level fields
REQUIRED_TOP_FIELDS = [
    'timestamp',
    'git_commit',
    'experiment_type',
    'run_tier',
    'primary_metric',
    'environment',
    'tx_power_dbm'
]

# Required config fields
REQUIRED_CONFIG_FIELDS = [
    'seeds',
    'node_counts',
    'round_counts',
    'dropout_rates'
]

# Valid values
VALID_RUN_TIERS = ['diagnostic', 'publication']
VALID_PRIMARY_METRICS = ['pdr_expected']
VALID_ENVIRONMENTS = [
    'indoor_office', 'indoor_factory',
    'outdoor_urban', 'outdoor_suburban',
    'multiple'
]


def validate_file(filepath: str, strict: bool = False) -> dict:
    """Validate a single JSON file"""
    result = {
        'file': filepath,
        'valid': True,
        'errors': [],
        'warnings': []
    }

    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except Exception as e:
        result['valid'] = False
        result['errors'].append(f"Cannot read JSON: {e}")
        return result

    # Check required top-level fields
    for field in REQUIRED_TOP_FIELDS:
        if field not in data:
            if strict:
                result['valid'] = False
                result['errors'].append(f"Missing top-level field: {field}")
            else:
                result['warnings'].append(f"Missing top-level field: {field}")

    # Check config fields
    if 'config' not in data:
        if strict:
            result['valid'] = False
            result['errors'].append("Missing config field")
        else:
            result['warnings'].append("Missing config field")
    else:
        for field in REQUIRED_CONFIG_FIELDS:
            if field not in data['config']:
                if strict:
                    result['valid'] = False
                    result['errors'].append(f"config missing field: {field}")
                else:
                    result['warnings'].append(f"config missing field: {field}")

    # Check valid values
    if 'run_tier' in data:
        if data['run_tier'] not in VALID_RUN_TIERS:
            result['errors'].append(f"Invalid run_tier: {data['run_tier']}")
            result['valid'] = False

    if 'primary_metric' in data:
        if data['primary_metric'] not in VALID_PRIMARY_METRICS:
            result['errors'].append(f"Invalid primary_metric: {data['primary_metric']}")
            result['valid'] = False

    if 'environment' in data:
        if data['environment'] not in VALID_ENVIRONMENTS:
            result['warnings'].append(f"Non-standard environment: {data['environment']}")

    # Check "multiple" consistency
    if data.get('tx_power_dbm') == 'multiple':
        if 'config' in data and 'tx_powers_dbm' not in data['config']:
            result['warnings'].append("tx_power_dbm='multiple' but config missing tx_powers_dbm")

    if data.get('environment') == 'multiple':
        if 'config' in data and 'environments' not in data['config']:
            result['warnings'].append("environment='multiple' but config missing environments")

    # Check patched_from/patch_note for patched files
    if 'patched_from' in data:
        if 'patch_note' not in data:
            result['warnings'].append("patched_from exists but patch_note missing")

    # Check raw_results
    if 'raw_results' not in data:
        result['warnings'].append("Missing raw_results field")

    return result


def parse_timestamp(filename: str) -> datetime:
    """Extract timestamp from filename"""
    try:
        # Pattern: xxx_YYYYMMDD_HHMMSS.json
        parts = filename.replace('.json', '').split('_')
        if len(parts) >= 2:
            date_str = parts[-2]
            time_str = parts[-1]
            if len(date_str) == 8 and len(time_str) == 6:
                return datetime.strptime(f"{date_str}_{time_str}", "%Y%m%d_%H%M%S")
    except Exception:
        pass
    return None


def main():
    parser = argparse.ArgumentParser(description='Validate result JSON metadata')
    parser.add_argument('files', nargs='*', help='JSON files to validate')
    parser.add_argument('--dir', default='results', help='Results directory')
    parser.add_argument('--strict', action='store_true',
                        help='Strict mode: missing fields are errors')
    parser.add_argument('--after', type=str,
                        help='Only check files after date (YYYYMMDD)')
    args = parser.parse_args()

    files_to_check = []
    after_date = None

    if args.after:
        try:
            after_date = datetime.strptime(args.after, "%Y%m%d")
        except ValueError:
            print(f"Invalid date format: {args.after}, use YYYYMMDD")
            return 1

    if args.files:
        files_to_check = args.files
    else:
        # Scan results directory
        results_dir = Path(args.dir)
        if results_dir.exists():
            for f in results_dir.glob('*.json'):
                if after_date:
                    ts = parse_timestamp(f.name)
                    if ts and ts < after_date:
                        continue
                files_to_check.append(f)

    if not files_to_check:
        print("No files to validate")
        return 1

    print(f"Validating {len(files_to_check)} files...")
    if args.strict:
        print("Mode: STRICT")
    if after_date:
        print(f"Filter: after {args.after}")
    print("=" * 60)

    total_valid = 0
    total_invalid = 0

    for filepath in files_to_check:
        result = validate_file(str(filepath), strict=args.strict)

        status = "[PASS]" if result['valid'] else "[FAIL]"
        print(f"\n{status} {Path(filepath).name}")

        if result['errors']:
            for err in result['errors']:
                print(f"  [ERROR] {err}")

        if result['warnings']:
            for warn in result['warnings']:
                print(f"  [WARN] {warn}")

        if result['valid']:
            total_valid += 1
        else:
            total_invalid += 1

    print("\n" + "=" * 60)
    print(f"Total: {total_valid} passed, {total_invalid} failed")

    return 0 if total_invalid == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
