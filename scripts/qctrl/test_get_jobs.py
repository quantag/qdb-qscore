#!/usr/bin/env python3
# test_jobs.py
# POST /jobs with qctrl_api_key from config.json

import argparse
import json
import sys
from pathlib import Path
import requests


def load_config(path: Path) -> dict:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            raise ValueError("config.json must contain a JSON object")
        return data
    except Exception as e:
        print(f"Error: failed to read config: {e}", file=sys.stderr)
        sys.exit(2)


def main():
    ap = argparse.ArgumentParser(
        description="Call /jobs endpoint with qctrl_api_key from config.json"
    )
    ap.add_argument(
        "--config",
        type=Path,
        default=Path("config.json"),
        help="Path to config.json (default: ./config.json)",
    )
    ap.add_argument(
        "--url",
        default="https://cloud.quantag-it.com/api21",
        help="Base service URL (default: https://cloud.quantag-it.com/api21)",
    )
    ap.add_argument(
        "--limit",
        type=int,
        default=50,
        help="Limit number of jobs to fetch (default: 50)",
    )
    ap.add_argument("--timeout", type=float, default=60.0)
    ap.add_argument("--name", help="Optional job name filter (e.g., execute)")
    ap.add_argument("--state", help="Optional state filter (e.g., STARTED, SUCCEEDED)")
    args = ap.parse_args()

    cfg = load_config(args.config)
    qctrl_api_key = cfg.get("qctrl_api_key")
    if not qctrl_api_key:
        print("Error: qctrl_api_key is missing in config.json", file=sys.stderr)
        sys.exit(2)

    payload = {
        "config": {"qctrl_api_key": qctrl_api_key},
        "limit": args.limit,
    }
    if args.name:
        payload["name"] = args.name
    if args.state:
        payload["state"] = args.state

    try:
        resp = requests.post(f"{args.url}/jobs", json=payload, timeout=args.timeout)
        resp.raise_for_status()
        data = resp.json()
        print(json.dumps(data, indent=2, sort_keys=True))
        sys.exit(0 if data.get("status") == 0 else 6)
    except requests.RequestException as e:
        print(f"HTTP error: {e}", file=sys.stderr)
        try:
            print(getattr(resp, "text", ""), file=sys.stderr)
        except Exception:
            pass
        sys.exit(1)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
