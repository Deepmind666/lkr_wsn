import os
import sys
import pkgutil
import site
import platform


def pv(k, v):
    print(f"{k}: {v}")


print("=== Python Environment Info ===")
pv("Python", sys.version)
pv("Executable", sys.executable)
pv("sys.prefix", sys.prefix)
pv("sys.base_prefix", sys.base_prefix)
pv("sys.path[0]", sys.path[0])

print("\n=== Key Environment Variables ===")
pv("VIRTUAL_ENV", os.environ.get("VIRTUAL_ENV"))
pv("PYTHONHOME", os.environ.get("PYTHONHOME"))
pv("PYTHONPATH", os.environ.get("PYTHONPATH"))
pv("CONDA_PREFIX", os.environ.get("CONDA_PREFIX"))
pv("CONDA_DEFAULT_ENV", os.environ.get("CONDA_DEFAULT_ENV"))

print("\n=== Platform ===")
pv("platform", platform.platform())

print("\n=== NumPy Visibility ===")
print("numpy found via pkgutil:", pkgutil.find_loader("numpy") is not None)
try:
    import numpy as np
    pv("numpy.__version__", np.__version__)
    pv("numpy.__file__", getattr(np, "__file__", "<n/a>"))
except Exception as e:
    print("numpy import error:", repr(e))

print("\n=== site.getsitepackages() ===")
try:
    print(site.getsitepackages())
except Exception as e:
    print("site.getsitepackages error:", repr(e))

print("\n=== sys.path ===")
for p in sys.path:
    print(" -", p)

print("\nDone.")