#!/usr/bin/env python3
"""Debug script for E0 experiment"""

import sys
import traceback

print("Starting debug...")

try:
    import numpy as np
    print(f"NumPy version: {np.__version__}")
except Exception as e:
    print(f"NumPy import error: {e}")
    sys.exit(1)

try:
    import pandas as pd
    print(f"Pandas version: {pd.__version__}")
except Exception as e:
    print(f"Pandas import error: {e}")
    sys.exit(1)

try:
    from scipy import stats
    print(f"SciPy stats imported")
except Exception as e:
    print(f"SciPy import error: {e}")
    sys.exit(1)

try:
    import gzip
    from pathlib import Path
    
    data_path = Path('data/Intel_Lab_Data/data.txt.gz')
    print(f"Loading data from {data_path}...")
    
    records = []
    with gzip.open(data_path, 'rt') as f:
        for i, line in enumerate(f):
            if i >= 10000:  # Only load 10k records for testing
                break
            parts = line.strip().split()
            if len(parts) >= 8:
                try:
                    record = {
                        'datetime': f"{parts[0]} {parts[1]}",
                        'epoch': int(parts[2]),
                        'moteid': int(parts[3]),
                        'temperature': float(parts[4]),
                        'humidity': float(parts[5]),
                        'light': float(parts[6]),
                        'voltage': float(parts[7])
                    }
                    records.append(record)
                except (ValueError, IndexError):
                    continue
    
    df = pd.DataFrame(records)
    print(f"Loaded {len(df)} records")
    print(f"Columns: {df.columns.tolist()}")
    print(f"Sample:\n{df.head()}")
    
    # Test correlation
    print("\nTesting correlation...")
    x = df['humidity'].values
    y = df['voltage'].values
    
    # Filter valid values
    mask = ~(np.isnan(x) | np.isnan(y) | np.isinf(x) | np.isinf(y))
    x = x[mask]
    y = y[mask]
    
    print(f"Valid samples: {len(x)}")
    print(f"X range: {x.min():.2f} - {x.max():.2f}")
    print(f"Y range: {y.min():.2f} - {y.max():.2f}")
    
    print(f"X std: {x.std():.6f}")
    print(f"Y std: {y.std():.6f}")
    print(f"X dtype: {x.dtype}")
    print(f"Y dtype: {y.dtype}")
    
    # Convert to float64 explicitly
    x = x.astype(np.float64)
    y = y.astype(np.float64)
    
    # Use smaller sample
    x_small = x[:1000]
    y_small = y[:1000]
    
    print(f"Testing with {len(x_small)} samples...")
    sys.stdout.flush()
    
    if x_small.std() == 0 or y_small.std() == 0:
        print("ERROR: Zero variance in data!")
    else:
        print("Computing correlation with numpy...")
        sys.stdout.flush()
        try:
            # Use numpy corrcoef instead of scipy
            corr_matrix = np.corrcoef(x_small, y_small)
            r = corr_matrix[0, 1]
            print(f"NumPy correlation r={r:.4f}")
            
            # Now try scipy
            print("Computing pearsonr with scipy...")
            sys.stdout.flush()
            r2, p = stats.pearsonr(x_small, y_small)
            print(f"SciPy Pearson r={r2:.4f}, p={p:.4e}")
        except Exception as e:
            print(f"Error: {e}")
            traceback.print_exc()
    
    print("\nDebug completed successfully!")
    
except Exception as e:
    print(f"Error: {e}")
    traceback.print_exc()
    sys.exit(1)
