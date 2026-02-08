import argparse
import hashlib
import os
import sys
import urllib.request


def _sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def download(url, out_path, expected_sha256=None):
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    print(f"Downloading: {url}")
    urllib.request.urlretrieve(url, out_path)
    print(f"Saved to: {out_path}")
    if expected_sha256:
        got = _sha256(out_path)
        if got.lower() != expected_sha256.lower():
            raise RuntimeError(f"SHA256 mismatch: {got} != {expected_sha256}")
        print("SHA256 OK")


def main():
    parser = argparse.ArgumentParser(
        description="Download SensorScope (or other) dataset assets. Provide a verified URL."
    )
    parser.add_argument("--url", required=True, help="Verified download URL (TODO: supply)")
    parser.add_argument("--out", required=True, help="Output file path")
    parser.add_argument("--sha256", default=None, help="Optional SHA256 for integrity check")
    args = parser.parse_args()

    try:
        download(args.url, args.out, args.sha256)
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
