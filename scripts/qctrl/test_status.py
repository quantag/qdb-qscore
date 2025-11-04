#!/usr/bin/env python3
# test_status.py
# One-shot status check that reads config.json and sends qctrl_api_key as a query param.

import argparse
import json
import sys
import requests
from pathlib import Path
from urllib.parse import urlencode

def load_config(config_path: Path) -> dict:
    try:
        data = json.loads(config_path.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            raise ValueError("config.json must contain a JSON object")
        return data
    except Exception as e:
        print(f"Error: failed to read config: {e}", file=sys.stderr)
        sys.exit(2)

def main():
    ap = argparse.ArgumentParser(description="GET /status/<action_id> once, with qctrl_api_key from config.json")
    ap.add_argument("action_id", help="Fire Opal action_id to check")
    ap.add_argument("--config", type=Path, default=Path("config.json"),
                    help="Path to config.json (default: ./config.json)")
    ap.add_argument("--url", default="https://cloud.quantag-it.com/api21",
                    help="Base service URL (default: https://cloud.quantag-it.com/api21)")
    ap.add_argument("--timeout", type=float, default=60.0,
                    help="HTTP timeout seconds (default: 60)")
    args = ap.parse_args()

    cfg = load_config(args.config)
    qctrl_api_key = cfg.get("qctrl_api_key")
    if not qctrl_api_key:
        print("Error: qctrl_api_key is missing in config.json", file=sys.stderr)
        sys.exit(2)

    # Compose endpoint: GET /status/<action_id>?qctrl_api_key=...
    query = urlencode({"qctrl_api_key": qctrl_api_key})
    endpoint = f"{args.url}/status/{args.action_id}?{query}"

    try:
        resp = requests.get(endpoint, timeout=args.timeout)
        resp.raise_for_status()
        data = resp.json()
        print(json.dumps(data, indent=2, sort_keys=True))
        # Exit code 0 only when {"status": 0}
        sys.exit(0 if isinstance(data.get("status"), int) and data["status"] == 0 else 6)
    except requests.RequestException as e:
        print(f"HTTP error: {e}", file=sys.stderr)
        # Try to print server body if present
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

