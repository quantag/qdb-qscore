#!/usr/bin/env python3
"""
submit_qasm.py

Load a .qasm file and a config.json (with Q-CTRL/IBM creds),
then POST to your Flask microservice.

Usage:
  python submit_qasm.py path/to/circuit.qasm \
    --config config.json \
    --url https://cloud.quantag-it.com/api21/run
"""

import argparse
import base64
import json
import sys
from pathlib import Path

import requests


def load_qasm_base64(qasm_path: Path) -> str:
    data = qasm_path.read_bytes()
    return base64.b64encode(data).decode("ascii")


def load_config(config_path: Path) -> dict:
    cfg = json.loads(config_path.read_text(encoding="utf-8"))
    if not isinstance(cfg, dict):
        raise ValueError("config.json must contain a JSON object")
    return cfg


def main() -> int:
    parser = argparse.ArgumentParser(description="Submit OpenQASM to Q-CTRL service")
    parser.add_argument("qasm", type=Path, help="Path to .qasm file")
    parser.add_argument("--config", type=Path, default=Path("config.json"),
                        help="Path to config.json (default: ./config.json)")
    parser.add_argument("--url", default="https://cloud.quantag-it.com/api21/run",
                        help="Service URL (default: https://cloud.quantag-it.com/api21/run)")
    parser.add_argument("--timeout", type=float, default=120.0,
                        help="HTTP timeout seconds (default: 120)")
    args = parser.parse_args()

    if not args.qasm.exists():
        print(f"ERROR: QASM file not found: {args.qasm}", file=sys.stderr)
        return 2
    if not args.config.exists():
        print(f"ERROR: config.json not found: {args.config}", file=sys.stderr)
        return 2

    try:
        src_b64 = load_qasm_base64(args.qasm)
        cfg = load_config(args.config)
    except Exception as e:
        print(f"ERROR: Failed to load inputs: {e}", file=sys.stderr)
        return 2

    payload = {
        "src": src_b64,
        "config": cfg,
    }

    headers = {"Content-Type": "application/json"}
    try:
        resp = requests.post(args.url, headers=headers, json=payload, timeout=args.timeout)
    except requests.RequestException as e:
        print(f"ERROR: HTTP request failed: {e}", file=sys.stderr)
        return 3

    # Non-2xx HTTP codes
    if not resp.ok:
        print(f"ERROR: Server returned HTTP {resp.status_code}", file=sys.stderr)
        try:
            print(resp.text, file=sys.stderr)
        except Exception:
            pass
        return 4

    # Expect JSON with integer field "status": 0 OK, non-zero error
    try:
        data = resp.json()
    except Exception as e:
        print(f"ERROR: Response is not valid JSON: {e}", file=sys.stderr)
        print(resp.text, file=sys.stderr)
        return 5

    status = data.get("status")
    # Your service returns either a flat {status, ...} or {status, ...} already.
    # Just print the whole response for convenience.
    print(json.dumps(data, indent=2, sort_keys=True))

    if isinstance(status, int) and status == 0:
        return 0
    else:
        # If status is missing or non-zero, treat as failure
        return 6


if __name__ == "__main__":
    sys.exit(main())
