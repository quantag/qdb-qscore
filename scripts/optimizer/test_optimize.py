import argparse
import base64
import json
import sys
from pathlib import Path

import requests


def b64encode_text(text: str) -> str:
    return base64.b64encode(text.encode("utf-8")).decode("ascii")


def b64decode_text(b64_str: str) -> str:
    return base64.b64decode(b64_str).decode("utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Send OpenQASM to Quantag optimizer microservice and save optimized QASM."
    )
    parser.add_argument(
        "qasm_file",
        type=str,
        help="Path to input .qasm file (OpenQASM 2 expected for BQSKit).",
    )
    parser.add_argument(
        "--type",
        dest="opt_type",
        type=int,
        default=0,
        help="Optimizer type. 0 = BQSKit. Others reserved.",
    )
    parser.add_argument(
        "--url",
        type=str,
        default="https://cloud.quantag-it.com/api4/optimize",
        help="Service endpoint URL.",
    )
    parser.add_argument(
        "--out",
        type=str,
        default=None,
        help="Output file path. Default: <input_basename>.optimized.qasm",
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=300,
        help="HTTP timeout in seconds.",
    )

    args = parser.parse_args()

    in_path = Path(args.qasm_file)
    if not in_path.exists():
        print("Error: input file does not exist: %s" % in_path)
        return 2

    qasm_in = in_path.read_text(encoding="utf-8")
    payload = {
        "type": args.opt_type,
        "src": b64encode_text(qasm_in),
    }

    try:
        resp = requests.post(args.url, json=payload, timeout=args.timeout)
    except Exception as e:
        print("HTTP request failed: %s" % e)
        return 3

    if resp.status_code >= 400:
        print("HTTP error: %s" % resp.status_code)
        try:
            print(resp.text)
        except Exception:
            pass
        return 4

    try:
        data = resp.json()
    except json.JSONDecodeError:
        print("Error: response is not valid JSON.")
        print(resp.text)
        return 5

    status = data.get("status", None)
    out_b64 = data.get("src", "")

    if status != 0:
        print("Service returned nonzero status: %s" % status)
        # Optional: save raw response for debugging
        debug_path = in_path.with_suffix(".reply.json")
        debug_path.write_text(json.dumps(data, indent=2), encoding="utf-8")
        print("Saved debug response to: %s" % debug_path)
        return 6

    try:
        qasm_out = b64decode_text(out_b64)
    except Exception as e:
        print("Failed to decode output base64: %s" % e)
        return 7

    if args.out is None:
        out_path = in_path.with_suffix("")  # remove .qasm
        out_path = Path(str(out_path) + ".optimized.qasm")
    else:
        out_path = Path(args.out)

    out_path.write_text(qasm_out, encoding="utf-8")
    print("OK. Optimized QASM written to: %s" % out_path)
    return 0


if __name__ == "__main__":
    sys.exit(main())
