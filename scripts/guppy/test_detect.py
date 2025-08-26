#!/usr/bin/env python3
# detect_test.py
# Usage:
#   python detect_test.py path/to/examples.py
#   optional:
#     --url https://cryspprod3.quantag-it.com:444/api17/detect
#     --out out_detect/response.json
#     --insecure         (skip TLS verification if using a self-signed cert)
#     --timeout 30

import argparse
import base64
import json
from pathlib import Path

import requests

DEFAULT_URL = "https://cryspprod3.quantag-it.com:444/api17/detect"

def main():
    ap = argparse.ArgumentParser(description="Test /detect endpoint for Guppy functions")
    ap.add_argument("source", help="Path to Guppy/Python source file")
    ap.add_argument("--url", default=DEFAULT_URL, help="Detect endpoint URL")
    ap.add_argument("--out", default=None, help="Optional path to save full JSON response")
    ap.add_argument("--insecure", action="store_true", help="Disable TLS verification")
    ap.add_argument("--timeout", type=float, default=30.0, help="HTTP timeout in seconds")
    args = ap.parse_args()

    src_path = Path(args.source)
    if not src_path.exists():
        print(f"Error: file not found: {src_path}")
        return 2

    src_text = src_path.read_text(encoding="utf-8")
    payload = {
        "source_b64": base64.b64encode(src_text.encode("utf-8")).decode("ascii")
    }

    try:
        resp = requests.post(args.url, json=payload, timeout=args.timeout, verify=not args.insecure)
    except requests.RequestException as e:
        print(f"HTTP error: {e}")
        return 2

    # Ensure JSON
    try:
        data = resp.json()
    except ValueError:
        print(f"Non-JSON response ({resp.status_code}): {resp.text[:500]}")
        return 2

    if args.out:
        out_path = Path(args.out)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(json.dumps(data, indent=2), encoding="utf-8")
        print(f"Saved full response to: {out_path}")

    if not resp.ok or not data.get("ok", False):
        err = data.get("error", f"HTTP {resp.status_code}")
        print(f"Service error: {err}")
        # If functions list is present, still print it
        funcs = data.get("functions")
        if funcs:
            print("Detected (partial):")
            for f in funcs:
                print(f" - {f.get('name')}  lines {f.get('lineno')}..{f.get('end_lineno')}")
        return 1
    print(data)
    # Pretty-print detected functions
    funcs = data.get("functions", [])
    count = data.get("count", len(funcs))
    print(f"OK. Detected {count} function(s).")
    if not funcs:
        return 0

    for f in funcs:
        name = f.get("name")
        lineno = f.get("lineno")
        end = f.get("end_lineno")
        sig = f.get("compile_sig")
        print(f" - {name}  lines {lineno}..{end}  compile{sig or '()'}")

    return 0

if __name__ == "__main__":
    raise SystemExit(main())
