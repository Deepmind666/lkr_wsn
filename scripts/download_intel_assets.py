#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import os, sys, requests

URLS = {
    'mote_locs.txt': 'https://db.csail.mit.edu/labdata/mote_locs.txt',
    # Note: connectivity probabilities file is not directly linked with a stable name; leave for manual placement if needed
}

if __name__ == '__main__':
    base = os.path.join(os.path.dirname(__file__), '..', 'data', 'Intel_Lab_Data')
    os.makedirs(base, exist_ok=True)
    for name, url in URLS.items():
        out = os.path.join(base, name)
        try:
            print('Downloading', url, '->', out)
            r = requests.get(url, timeout=30)
            r.raise_for_status()
            with open(out, 'wb') as f:
                f.write(r.content)
            print('Saved', out, f'({len(r.content)} bytes)')
        except Exception as e:
            print('Failed to download', url, 'error=', e)
            print('You can manually place the file at:', out)
    print('Done.')

