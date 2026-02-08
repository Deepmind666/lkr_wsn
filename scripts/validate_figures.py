#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Validate figures in given directories for basic quality checks:
- File naming: ASCII letters/digits/_- only; no spaces
- PNG: parse IHDR to get width/height; enforce min width
- SVG: regex for viewBox/width/height; enforce min width; check presence of <text>
- PDF: record presence; manual check required
Outputs a Markdown summary and a JSON report.
Uses only Python stdlib to avoid environment issues.
"""
import os
import re
import sys
import json
import struct
from typing import Dict, List, Tuple, Any

ASCII_NAME_RE = re.compile(r'^[A-Za-z0-9._-]+$')
SVG_VIEWBOX_RE = re.compile(r'viewBox\s*=\s*"([^"]+)"')
SVG_WIDTH_RE = re.compile(r'width\s*=\s*"([0-9.]+)\s*(px|pt)?"')
SVG_HEIGHT_RE = re.compile(r'height\s*=\s*"([0-9.]+)\s*(px|pt)?"')
MIN_WIDTH_PX = 1200
ASSUMED_SVG_DPI = int(os.environ.get('SVG_DPI', '300'))


def is_ascii_name(name: str) -> bool:
    return ASCII_NAME_RE.match(name) is not None


def parse_png_size(path: str) -> Tuple[int, int]:
    with open(path, 'rb') as f:
        sig = f.read(8)
        if sig != b'\x89PNG\r\n\x1a\n':
            return (0, 0)
        # Read chunks until IHDR
        while True:
            chunk_header = f.read(8)
            if len(chunk_header) < 8:
                return (0, 0)
            length, chunk_type = struct.unpack('>I4s', chunk_header)
            data = f.read(length)
            _crc = f.read(4)
            if chunk_type == b'IHDR' and len(data) >= 8:
                width, height = struct.unpack('>II', data[:8])
                return (int(width), int(height))
    return (0, 0)


def _svg_len_to_px(value: float, unit: str) -> int:
    try:
        if unit == 'pt':
            return int(round(value * (ASSUMED_SVG_DPI / 72.0)))
        return int(round(value))
    except Exception:
        return 0


def parse_svg_dims(text: str) -> Tuple[int, int]:
    mw = SVG_WIDTH_RE.search(text)
    mh = SVG_HEIGHT_RE.search(text)
    if mw and mh:
        try:
            w = float(mw.group(1))
            wu = (mw.group(2) or 'px').lower()
            h = float(mh.group(1))
            hu = (mh.group(2) or 'px').lower()
            return (_svg_len_to_px(w, wu), _svg_len_to_px(h, hu))
        except Exception:
            pass
    # Prefer viewBox as a fallback (assume user units are px)
    m = SVG_VIEWBOX_RE.search(text)
    if m:
        parts = m.group(1).strip().split()
        if len(parts) == 4:
            try:
                vw = float(parts[2])
                vh = float(parts[3])
                return (int(round(vw)), int(round(vh)))
            except Exception:
                pass
    return (0, 0)


def validate_dir(dir_path: str) -> Dict[str, Any]:
    report = {
        'directory': dir_path,
        'files': [],
        'summary': {
            'count': 0,
            'ok': 0,
            'warnings': 0,
            'errors': 0
        }
    }
    if not os.path.isdir(dir_path):
        report['summary']['errors'] += 1
        return report
    for name in sorted(os.listdir(dir_path)):
        path = os.path.join(dir_path, name)
        if os.path.isdir(path):
            # Skip subdirs at top-level; they can be validated separately
            continue
        ext = os.path.splitext(name)[1].lower()
        item = {
            'name': name,
            'path': path,
            'type': ext,
            'issues': [],
            'width': None,
            'height': None
        }
        # Naming check
        if not is_ascii_name(name):
            item['issues'].append('ERROR: Non-ASCII or invalid filename characters')
        if ' ' in name:
            item['issues'].append('ERROR: Filename contains spaces')
        # Type-specific checks
        if ext == '.png':
            w, h = parse_png_size(path)
            item['width'], item['height'] = w, h
            if w == 0:
                item['issues'].append('ERROR: PNG size parse failed')
            else:
                if w < MIN_WIDTH_PX:
                    item['issues'].append(f'WARNING: PNG width {w}px < {MIN_WIDTH_PX}px')
        elif ext == '.svg':
            try:
                with open(path, 'r', encoding='utf-8', errors='ignore') as f:
                    text = f.read()
                w, h = parse_svg_dims(text)
                item['width'], item['height'] = w, h
                if w and w < MIN_WIDTH_PX:
                    item['issues'].append(f'WARNING: SVG width {w} < {MIN_WIDTH_PX}')
                if '<text' not in text:
                    item['issues'].append('WARNING: SVG may lack text labels (<text> not found)')
                # Simple heuristic: ensure no obvious hidden overflow
                if 'clipPath' in text:
                    item['issues'].append('INFO: SVG uses clipPath (check for potential occlusions)')
            except Exception as e:
                item['issues'].append(f'ERROR: SVG parse error: {e}')
        elif ext == '.pdf':
            item['issues'].append('INFO: PDF detected; manual font/embedding check required')
        else:
            item['issues'].append('INFO: Unchecked file type')
        # Update summary
        report['files'].append(item)
    # Summaries
    report['summary']['count'] = len(report['files'])
    for it in report['files']:
        has_error = any(msg.startswith('ERROR') for msg in it['issues'])
        has_warning = any(msg.startswith('WARNING') for msg in it['issues'])
        if has_error:
            report['summary']['errors'] += 1
        elif has_warning:
            report['summary']['warnings'] += 1
        else:
            report['summary']['ok'] += 1
    return report


def write_markdown(out_md: str, reports: List[Dict[str, Any]]):
    lines = []
    lines.append('# Figure Validation Report\n')
    lines.append('自动化检查范围：命名、尺寸、基本标注（SVG）。详细格式与数据准确需人工二次审查。\n')
    for rep in reports:
        s = rep['summary']
        lines.append(f"\n## Directory: {rep['directory']}\n")
        lines.append(f"- 总数: {s['count']}  OK: {s['ok']}  Warnings: {s['warnings']}  Errors: {s['errors']}\n")
        for it in rep['files']:
            dims = ''
            if it['width']:
                dims = f" ({it['width']}x{it['height']})"
            lines.append(f"- {it['name']}{dims}")
            if it['issues']:
                for msg in it['issues']:
                    lines.append(f"  - {msg}")
            else:
                lines.append("  - OK")
    with open(out_md, 'w', encoding='utf-8') as f:
        f.write('\n'.join(lines))


def main(argv: List[str]):
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument('--dirs', nargs='+', required=True, help='Directories to validate')
    ap.add_argument('--out', default='results/figure_validation_report.md', help='Markdown output path')
    ap.add_argument('--json', default='results/figure_validation_report.json', help='JSON output path')
    args = ap.parse_args(argv)

    reports = [validate_dir(d) for d in args.dirs]
    out_json = {
        'reports': reports,
        'policy': {
            'min_width_px': MIN_WIDTH_PX,
            'assumed_svg_dpi': ASSUMED_SVG_DPI,
            'name_regex': ASCII_NAME_RE.pattern,
            'notes': 'Manual review required for font embedding, occlusion, and data accuracy.'
        }
    }
    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    write_markdown(args.out, reports)
    with open(args.json, 'w', encoding='utf-8') as f:
        json.dump(out_json, f, ensure_ascii=False, indent=2)
    print(f"Wrote: {args.out} and {args.json}")


if __name__ == '__main__':
    main(sys.argv[1:])