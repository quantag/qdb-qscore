#!/usr/bin/env python3
# submit_ibm_job_test.py

import argparse
import base64
import json
import sys
from pathlib import Path

import requests


DEFAULT_URL = "https://quantum.quantag-it.com/api5/submit_ibm_job"


def load_config(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def read_qasm_b64(path: Path) -> str:
    data = path.read_bytes()
    return base64.b64encode(data).decode("ascii")


def main():
    parser = argparse.ArgumentParser(
        description="Submit an IBM job by posting base64 QASM to /submit_ibm_job."
    )
    parser.add_argument("qasm_file", help="Path to .qasm file")
    parser.add_argument(
        "--config",
        default="config.json",
        help="Path to config.json (default: ./config.json)",
    )
    parser.add_argument(
        "--url",
        default=DEFAULT_URL,
        help=f"Endpoint URL (default: {DEFAULT_URL})",
    )
    parser.add_argument(
        "--insecure",
        action="store_true",
        help="Disable TLS verification (use only for testing).",
    )
    args = parser.parse_args()

    qasm_path = Path(args.qasm_file)
    cfg_path = Path(args.config)

    if not qasm_path.is_file():
        print(f"Error: QASM file not found: {qasm_path}", file=sys.stderr)
        sys.exit(2)

    if not cfg_path.is_file():
        print(f"Error: config.json not found: {cfg_path}", file=sys.stderr)
        sys.exit(2)

    cfg = load_config(cfg_path)

    # Required by your /submit_ibm_job route:
    # qasm (base64), user_id, token, instance, backend
    # See server.py checks. :contentReference[oaicite:1]{index=1}
    missing = [k for k in ("user_id", "token", "instance", "backend") if k not in cfg]
    if missing:
        print(f"Error: config.json missing keys: {', '.join(missing)}", file=sys.stderr)
        sys.exit(2)

    qasm_b64 = read_qasm_b64(qasm_path)

    payload = {
        "qasm": qasm_b64,
        "user_id": cfg["user_id"],
        "token": cfg["token"],
        "instance": cfg["instance"],
        "backend": cfg["backend"],
    }

    # Optional pass-through: if shots present in config, include it (harmless if ignored by server)
    if "shots" in cfg:
        payload["shots"] = cfg["shots"]

    try:
        resp = requests.post(args.url, json=payload, timeout=60, verify=not args.insecure)
    except requests.RequestException as e:
        print(f"HTTP error: {e}", file=sys.stderr)
        sys.exit(1)

    print(f"Status: {resp.status_code}")
    try:
        print(json.dumps(resp.json(), indent=2))
    except ValueError:
        print(resp.text)


if __name__ == "__main__":
    main()
