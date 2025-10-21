#!/usr/bin/env python3
# test_result.py
# One-shot GET /result/<action_id> using qctrl_api_key from config.json

import argparse
import json
import sys
from pathlib import Path
from urllib.parse import urlencode

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
        description="GET /result/<action_id> once, passing qctrl_api_key from config.json"
    )
    ap.add_argument("action_id", help="Fire Opal action_id to fetch")
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
        "--timeout",
        type=float,
        default=600.0,
        help="HTTP timeout seconds (default: 600)",
    )
    args = ap.parse_args()

    cfg = load_config(args.config)
    qctrl_api_key = cfg.get("qctrl_api_key")
    if not qctrl_api_key:
        print("Error: qctrl_api_key is missing in config.json", file=sys.stderr)
        sys.exit(2)

    endpoint = f"{args.url}/result/{args.action_id}?{urlencode({'qctrl_api_key': qctrl_api_key})}"

    try:
        resp = requests.get(endpoint, timeout=args.timeout)
        resp.raise_for_status()
        data = resp.json()
        print(json.dumps(data, indent=2, sort_keys=True))
        # Exit 0 only if {"status": 0}
        sys.exit(0 if isinstance(data.get("status"), int) and data["status"] == 0 else 6)
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
