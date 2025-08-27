#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import os, sys, requests

TEMPLATES = [
    {
        'name': 'ieee_access',
        'url': 'https://mirrors.ctan.org/macros/latex/contrib/IEEEtran.zip',
        'outfile': 'IEEEtran.zip',
        'note': 'Generic IEEEtran LaTeX class (commonly used for IEEE Access). Unzip and use bare_jrnl.tex / bare_adv.tex as starting points.'
    },
    {
        'name': 'mdpi_latex',
        'url': 'https://github.com/mdpi/latex/archive/refs/heads/master.zip',
        'outfile': 'mdpi_latex_master.zip',
        'note': 'MDPI LaTeX class for journals (including Sensors). See template.tex and mdpi.cls; follow Sensors author instructions.'
    }
]

if __name__ == '__main__':
    base = os.path.join(os.path.dirname(__file__), '..', 'docs', 'templates')
    os.makedirs(base, exist_ok=True)
    for t in TEMPLATES:
        sub = os.path.join(base, t['name'])
        os.makedirs(sub, exist_ok=True)
        out = os.path.join(sub, t['outfile'])
        print('Downloading', t['name'], 'from', t['url'])
        try:
            r = requests.get(t['url'], timeout=60)
            r.raise_for_status()
            with open(out, 'wb') as f:
                f.write(r.content)
            # write a short README
            readme = os.path.join(sub, 'README.txt')
            with open(readme, 'w', encoding='utf-8') as rf:
                rf.write(f"Template: {t['name']}\nURL: {t['url']}\nSaved: {out}\nNote: {t['note']}\n")
            print('Saved to', out)
        except Exception as e:
            print('Failed to download', t['name'], 'error=', e)
    print('Done. Templates are under docs/templates/.')

