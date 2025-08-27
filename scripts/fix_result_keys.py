#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import os, sys, json, glob, shutil

if __name__ == '__main__':
    results_dir = os.path.join(os.path.dirname(__file__), '..', 'results')
    files = glob.glob(os.path.join(results_dir, '*.json'))
    fixed = 0
    for fp in files:
        try:
            with open(fp, 'r', encoding='utf-8') as f:
                data = json.load(f)
        except Exception:
            continue
        # recursively fix in dicts/lists
        def fix(obj):
            if isinstance(obj, dict):
                if 'packet_deliveryy_ratio_end2end' in obj and 'packet_delivery_ratio_end2end' not in obj:
                    obj['packet_delivery_ratio_end2end'] = obj.pop('packet_deliveryy_ratio_end2end')
                for k,v in list(obj.items()):
                    fix(v)
            elif isinstance(obj, list):
                for it in obj:
                    fix(it)
        before = json.dumps(data, ensure_ascii=False, sort_keys=True)
        fix(data)
        after = json.dumps(data, ensure_ascii=False, sort_keys=True)
        if before != after:
            bak = fp + '.bak'
            shutil.copyfile(fp, bak)
            with open(fp, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            fixed += 1
            print('Fixed keys in', fp, 'backup at', bak)
    print('Done. Fixed files:', fixed)

