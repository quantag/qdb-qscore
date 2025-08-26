#!/usr/bin/env python3
# guppy_compile_service.py
#
# Simple Flask service:
# POST /compile  with JSON:
# {
#   "source_b64": "<base64 of python module containing @guppy funcs>",
#   "functions": ["bell", "ghz10"],           # optional; if omitted, auto-detect
#   "formats": ["bytes_b64","json","str"]     # any subset; default: ["bytes_b64"]
# }
#
# Response:
# {
#   "ok": true,
#   "results": {
#     "bell": {"bytes_b64":"...", "json":"...", "str":"..."},
#     "ghz10": {...}
#   }
# }
#
# WARNING: This example uses exec() to load untrusted code. Do NOT expose publicly
# without sandboxing (containers, seccomp, timeouts, resource limits).

import base64
import io
import json
import os
import sys
from typing import Dict, Any, List

from flask import Flask, request, jsonify
import inspect
from typing import Tuple, List, Dict, Any
import ast

# You need guppylang installed:
# pip install guppylang
from guppylang import guppy
import importlib.util
import sys
import tempfile
from pathlib import Path

# Optional: if you plan to run in Selene locally later
# pip install selene-sim
# from selene_sim import build as selene_build

app = Flask(__name__)

DEFAULT_FORMATS = ["bytes_b64"]

import ast
import inspect
from typing import Any, Dict, List, Tuple

def detect_guppy_functions(src_code: str) -> Tuple[Dict[str, Any], List[Dict[str, Any]]]:
    ns: Dict[str, Any] = {}
    exec(src_code, ns, ns)  # WARNING: untrusted code; sandbox in production

    infos: List[Dict[str, Any]] = []

    skip_names = {"guppy", "qubit", "h", "cx", "x", "z", "measure_array"}

    # Build AST map: function_name -> (lineno, end_lineno)
    line_map: Dict[str, Tuple[int, int]] = {}
    try:
        tree = ast.parse(src_code)
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                line_map[node.name] = (
                    getattr(node, "lineno", None),
                    getattr(node, "end_lineno", None)
                )
    except Exception:
        pass

    for name, obj in ns.items():
        if name in skip_names:
            continue
        if not callable(obj):
            continue

        comp = getattr(obj, "compile", None)
        if comp is None or not callable(comp):
            continue

        try:
            compile_sig = str(inspect.signature(comp))
        except Exception:
            compile_sig = None

        lineno, end_lineno = line_map.get(name, (None, None))

        infos.append({
            "name": name,
            "lineno": lineno,
            "end_lineno": end_lineno,
            "has_compile": True,
            "compile_sig": compile_sig,
        })

    return ns, infos


@app.route("/compile", methods=["POST"])
def compile_endpoint():
    try:
        data = request.get_json(force=True)
    except Exception:
        return jsonify({"ok": False, "error": "Invalid JSON"}), 400

    if not data or "source_b64" not in data:
        return jsonify({"ok": False, "error": "Missing 'source_b64'"}), 400

    try:
        src = base64.b64decode(data["source_b64"]).decode("utf-8")
    except Exception as e:
        return jsonify({"ok": False, "error": f"Base64 decode failed: {e}"}), 400

    func_names = data.get("functions")
    if not func_names:
        return jsonify({"ok": False, "error": "Missing 'functions' array"}), 400

    formats = data.get("formats") or ["bytes_b64"]

    # --- Save source into a temp file ---
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir) / "user_module.py"
        tmp_path.write_text(src, encoding="utf-8")

        # --- Load as module ---
        module_name = f"user_module_{os.getpid()}"
        spec = importlib.util.spec_from_file_location(module_name, tmp_path)
        mod = importlib.util.module_from_spec(spec)
        sys.modules[module_name] = mod
        try:
            spec.loader.exec_module(mod)  # actually import code
        except Exception as e:
            return jsonify({"ok": False, "error": f"Execution failed: {e}"}), 400

        results: Dict[str, Any] = {}

        for name in func_names:
            if not hasattr(mod, name):
                return jsonify({"ok": False, "error": f"Function '{name}' not found"}), 400
            fn = getattr(mod, name)

            try:
                compiled = fn.compile()
            except Exception as e:
                return jsonify({"ok": False, "error": f"Compile failed for '{name}': {e}"}), 400

            entry = {}
            if "bytes_b64" in formats:
                entry["bytes_b64"] = base64.b64encode(compiled.to_bytes()).decode("ascii")
            if "str" in formats:
                try:
                    entry["str"] = compiled.to_str()
                except Exception as e:
                    entry["str_error"] = str(e)
            if "json" in formats and hasattr(compiled, "to_json"):
                try:
                    entry["json"] = compiled.to_json()
                except Exception as e:
                    entry["json_error"] = str(e)

            results[name] = entry

    return jsonify({"ok": True, "results": results})



@app.route("/health", methods=["GET"])
def health():
    return jsonify({"ok": True})


@app.route("/detect", methods=["POST"])
def detect_endpoint():
    try:
        data = request.get_json(force=True)
    except Exception:
        return jsonify({"ok": False, "error": "Invalid JSON"}), 400

    if not data or "source_b64" not in data:
        return jsonify({"ok": False, "error": "Missing 'source_b64'"}), 400

    try:
        src = base64.b64decode(data["source_b64"]).decode("utf-8")
    except Exception as e:
        return jsonify({"ok": False, "error": f"Base64 decode failed: {e}"}), 400

    try:
        _, infos = detect_guppy_functions(src)
    except Exception as e:
        return jsonify({"ok": False, "error": f"Execution/detection failed: {e}"}), 400

    return jsonify({
        "ok": True,
        "count": len(infos),
        "functions": infos
    })



if __name__ == "__main__":
    import logging
    logging.basicConfig(level=logging.DEBUG)  # Set to INFO or WARNING in prod
    app.run(debug=False, port=5038)
