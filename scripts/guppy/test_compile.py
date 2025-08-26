#!/usr/bin/env python3
# test_compile_client.py
# Usage:
#   python test_compile_client.py path/to/guppy_module.py
#   optional:
#     --functions bell,ghz3
#     --formats bytes_b64,json,str
#     --outdir out
#     --insecure
#     --timeout 60

import argparse
import base64
import json
import sys
from pathlib import Path

import requests

API_BASE = "https://cryspprod3.quantag-it.com:444/api17"
ENDPOINT_COMPILE = f"{API_BASE}/compile"
ENDPOINT_DETECT = f"{API_BASE}/detect"


def parse_args():
    p = argparse.ArgumentParser(description="Client for Guppy compile microservice")
    p.add_argument("source", help="Path to Guppy/Python source file")
    p.add_argument("--functions", help="Comma-separated function names; omit to auto-detect", default=None)
    p.add_argument("--formats", help="Comma-separated formats: hugr,json,str", default="hugr,json,str")
    p.add_argument("--outdir", help="Directory to write outputs", default="out_build")
    p.add_argument("--insecure", action="store_true", help="Disable TLS verification")
    p.add_argument("--timeout", type=float, default=60.0, help="HTTP timeout seconds")
    return p.parse_args()


def load_source(path: str) -> str:
    return Path(path).read_text(encoding="utf-8")


def detect_functions(src_b64: str, verify: bool, timeout: float):
    payload = {"source_b64": src_b64}
    try:
        resp = requests.post(ENDPOINT_DETECT, json=payload, timeout=timeout, verify=verify)
        resp.raise_for_status()
        data = resp.json()
    except Exception as e:
        print(f"Error calling /detect: {e}", file=sys.stderr)
        return []

    if not data.get("ok"):
        print(f"/detect returned error: {data}", file=sys.stderr)
        return []

    funcs = [f["name"] for f in data.get("functions", [])]
    print(f"/detect found {len(funcs)} functions: {funcs}")
    return funcs


def main():
    args = parse_args()
    src_path = Path(args.source)
    if not src_path.exists():
        print(f"Error: source file not found: {src_path}", file=sys.stderr)
        sys.exit(1)

    src_code = load_source(str(src_path))
    src_b64 = base64.b64encode(src_code.encode("utf-8")).decode("ascii")

    formats = [s.strip() for s in args.formats.split(",") if s.strip()]

    func_names = None
    if args.functions:
        func_names = [s.strip() for s in args.functions.split(",") if s.strip()]
    else:
        func_names = detect_functions(src_b64, verify=not args.insecure, timeout=args.timeout)
        if not func_names:
            print("No functions to compile, exiting.", file=sys.stderr)
            sys.exit(1)

    payload = {
        "source_b64": src_b64,
        "functions": func_names,
        "formats": formats,
    }

    try:
        resp = requests.post(
            ENDPOINT_COMPILE,
            json=payload,
            timeout=args.timeout,
            verify=not args.insecure,
        )
    except requests.RequestException as e:
        print(f"HTTP error: {e}", file=sys.stderr)
        sys.exit(1)

    try:
        resp_json = resp.json()
    except ValueError:
        print(f"Non-JSON response ({resp.status_code}): {resp.text}", file=sys.stderr)
        sys.exit(1)

    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)
    (outdir / "response.json").write_text(json.dumps(resp_json, indent=2), encoding="utf-8")

    if not resp.ok or not resp_json.get("ok", False):
        print(f"Compile failed: {resp_json}", file=sys.stderr)
        sys.exit(1)

    results = resp_json.get("results", {})
    for fname, artefacts in results.items():
        fdir = outdir / fname
        fdir.mkdir(parents=True, exist_ok=True)

        if "hugr" in artefacts:
            raw = base64.b64decode(artefacts["hugr"])
            (fdir / f"{fname}.hugr").write_bytes(raw)
            print(f"Wrote {fdir/fname}.hugr")

        if "json" in artefacts:
            (fdir / f"{fname}.hugr.json").write_text(
                artefacts["json"] if isinstance(artefacts["json"], str) else json.dumps(artefacts["json"], indent=2),
                encoding="utf-8",
            )
            print(f"Wrote {fdir/fname}.hugr.json")

        if "str" in artefacts:
            (fdir / f"{fname}.hugr.txt").write_text(artefacts["str"], encoding="utf-8")
            print(f"Wrote {fdir/fname}.hugr.txt")

    print(f"Done. Full response saved to {outdir/'response.json'}")


if __name__ == "__main__":
    main()
