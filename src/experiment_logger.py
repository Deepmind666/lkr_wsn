#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Simple experiment logger: append JSONL entries under results/logs.
Each entry includes timestamp, scenario, params, and key results.
"""
from __future__ import annotations
import os, json, time
from typing import Any, Dict

class ExperimentLogger:
    def __init__(self, log_dir: str = None, log_file: str = None):
        base_dir = os.path.join(os.path.dirname(__file__), '..', 'results', 'logs')
        self.log_dir = os.path.abspath(log_dir or base_dir)
        os.makedirs(self.log_dir, exist_ok=True)
        self.log_path = os.path.join(self.log_dir, log_file or 'exp_log.jsonl')

    def log(self, scenario: str, params: Dict[str, Any], results: Dict[str, Any]):
        entry = {
            'ts': time.strftime('%Y-%m-%d %H:%M:%S', time.localtime()),
            'scenario': scenario,
            'params': params,
            'results': results,
        }
        with open(self.log_path, 'a', encoding='utf-8') as f:
            f.write(json.dumps(entry, ensure_ascii=False) + '\n')
        return self.log_path

