import base64
import json
import os
import traceback
from typing import Any, Dict, List, Optional, Tuple

from flask import Flask, jsonify, request
from flask_cors import CORS

# Optional: Qiskit for QASM3 parsing fallback
try:
    from qiskit import QuantumCircuit
    _HAS_QISKIT = True
except Exception:
    _HAS_QISKIT = False

# PyZX is the workhorse for ZX + (best-effort) MBQC extraction
import pyzx as zx

app = Flask(__name__)
CORS(app)


# ---------------------------
# Utilities
# ---------------------------

def _decode_b64_src(src_b64: str) -> str:
    try:
        return base64.b64decode(src_b64).decode("utf-8")
    except Exception as e:
        raise ValueError(f"Failed to decode base64 'src': {e}")

def _load_pyzx_circuit_from_qasm(qasm_str: str) -> zx.Circuit:
    """
    Prefer native PyZX QASM (OpenQASM 2.x). If it fails and Qiskit is present,
    try QASM3 - Qiskit - PyZX.
    """
    # 1) Try PyZX native reader (QASM2)
    try:
        return zx.Circuit.from_qasm(qasm_str)
    except Exception:
        pass

    # 2) Try Qiskit (QASM2 or QASM3), then convert to PyZX if possible
    if not _HAS_QISKIT:
        # No Qiskit fallback available
        raise ValueError(
            "Could not parse with PyZX (likely QASM3). Qiskit is not installed for fallback parsing."
        )

    # Qiskit >=0.43 supports QuantumCircuit.from_qasm_str for QASM2.
    # For QASM3, the same method works in newer versions; otherwise, user needs qasm3 import.
    try:
        qc = QuantumCircuit.from_qasm_str(qasm_str)
    except Exception as e:
        raise ValueError(f"Qiskit failed to parse QASM (is it valid QASM2/3?): {e}")

    # Convert Qiskit circuit - PyZX circuit
    # PyZX provides Circuit.from_qiskit in modern versions.
    try:
        pyzx_circ = zx.Circuit.from_qiskit(qc)
        return pyzx_circ
    except Exception as e:
        raise RuntimeError(
            "Parsed with Qiskit but failed to convert to PyZX. "
            "Ensure pyzx >= 0.7 and qiskit are compatible. "
            f"Details: {e}"
        )

def _zx_graph_from_circuit(circ: zx.Circuit) -> zx.graph.graph_s.GraphS:
    """
    Convert a PyZX Circuit to a ZX-graph (GraphS).
    """
    return circ.to_graph()

def _serialize_zx_graph(g: zx.graph.graph_s.GraphS) -> Dict[str, Any]:
    """
    Return a JSON-serializable dict describing the ZX graph:
      - vertices with attributes (type, phase, qubit/time, boundary info)
      - undirected edges
    Falls back to a minimal schema if certain attrs are unavailable.
    """
    # Vertex packing
    verts = []
    for v in g.vertices():
        data = {
            "id": int(v),
            "type": str(g.type(v)),   # Z, X, H, BOUNDARY, etc.
            "phase": float(g.phase(v)) if g.phase(v) is not None else 0.0,
        }
        # Many graphs store "qubit" and "row" (time) on boundary vertices
        try:
            if g.qubit(v) is not None:
                data["qubit"] = int(g.qubit(v))
        except Exception:
            pass
        try:
            if g.row(v) is not None:
                data["row"] = int(g.row(v))
        except Exception:
            pass
        verts.append(data)

    # Edges (undirected)
    edges = []
    for e in g.edges():
        try:
            s, t = g.edge_st(e)
        except Exception:
            # Older PyZX may represent edges differently
            s, t = e
        edges.append([int(s), int(t)])

    return {"vertices": verts, "edges": edges}

def _try_extract_mbqc(g: zx.graph.graph_s.GraphS) -> Dict[str, Any]:
    """
    Best-effort MBQC extraction using gFlow/eFlow where available.
    Not all ZX graphs admit a simple MBQC pattern directly; we return
    helpful diagnostics when extraction is not possible.

    Output schema:
    {
      "supported": True/False,
      "order": [vertex ids...],
      "measurements": [{"v": id, "basis": "...", "angle": float}, ...],
      "feedforward": {"target_v":[source_vs...]},
      "notes": "..."
    }
    """
    # Attempt flow extraction
    try:
        flow = zx.flow.extract_flow(g)  # returns an object with .order, .successors, etc (version-dependent)
    except Exception as e:
        return {
            "supported": False,
            "notes": f"Could not extract flow (MBQC order) from graph: {e}"
        }

    # Order
    try:
        meas_order = list(flow.order)  # list of vertex ids
    except Exception:
        # Fallback: some versions expose a dict mapping or a method
        try:
            meas_order = list(getattr(flow, "measurement_order", []))
        except Exception:
            meas_order = []

    # Feedforward dependencies
    feedforward = {}
    try:
        # Common structure: flow.successors[v] gives deps to correct later vertices
        successors = getattr(flow, "successors", {})
        # Convert possible set-like to JSON-friendly lists
        for k, vs in (successors.items() if isinstance(successors, dict) else []):
            feedforward[str(int(k))] = [int(x) for x in vs]
    except Exception:
        # Not fatal; leave empty
        pass

    # Measurement bases/angles (heuristic; exact basis depends on graph normal form)
    # Here we provide a very conservative placeholder: Z/X spiders imply X/Z-type measurements
    # with phase as angle. A production tool would normal-form the graph first.
    measurements = []
    try:
        for v in meas_order:
            vtype = str(g.type(v))
            angle = float(g.phase(v)) if g.phase(v) is not None else 0.0
            if vtype.upper().startswith("Z"):
                basis = "X-basis (derived from Z-spider)"
            elif vtype.upper().startswith("X"):
                basis = "Z-basis (derived from X-spider)"
            else:
                basis = f"{vtype}-derived"
            measurements.append({"v": int(v), "basis": basis, "angle": angle})
    except Exception:
        pass

    return {
        "supported": True,
        "order": [int(v) for v in meas_order],
        "measurements": measurements,
        "feedforward": feedforward,
        "notes": (
            "MBQC pattern is best-effort from ZX flow. For precise patterns, put the graph in a normal form "
            "(e.g., graph-like form) and derive bases via a dedicated MBQC pass."
        ),
    }


# ---------------------------
# Routes
# ---------------------------

@app.route('/health', methods=['GET'])
def health():
    return jsonify({"status": 0}), 200

@app.route("/version", methods=["GET"])
def version() -> Tuple[str, int, Dict[str, str]]:
    lib_versions = {
        "pyzx": getattr(zx, "__version__", "unknown"),
        "qiskit_available": _HAS_QISKIT,
    }
    return jsonify(lib_versions), 200, {"Content-Type": "application/json"}

@app.route("/translate", methods=["POST"])
def translate():
    """
    POST JSON body:
    {
      "src": "<base64 OpenQASM string>",          # required
      "output": "all" | "zx" | "mbqc",            # optional (default: "all")
      "include_positions": false                  # optional (reserved; for layout embedding)
    }
    """
    try:
        data = request.get_json(force=True, silent=False) or {}
        src_b64 = data.get("src", "")
        if not src_b64:
            return jsonify({"error": "Missing 'src' (base64-encoded OpenQASM)."}), 400

        output_mode = data.get("output", "all").lower()
        qasm = _decode_b64_src(src_b64)

        # Build PyZX circuit (QASM2 - PyZX; QASM3 - Qiskit - PyZX)
        circ = _load_pyzx_circuit_from_qasm(qasm)

        # Convert to ZX graph
        g = _zx_graph_from_circuit(circ)
        zx_json = _serialize_zx_graph(g)

        resp = {"zx_graph": zx_json}

        # MBQC extraction (best effort)
        if output_mode in ("all", "mbqc"):
            mbqc = _try_extract_mbqc(g)
            resp["mbqc_pattern"] = mbqc

        return jsonify(resp), 200

    except Exception as e:
        tb = traceback.format_exc()
        return (
            jsonify({
                "error": str(e),
                "traceback": tb,
                "hint": (
                    "Ensure pyzx is installed (and qiskit if using QASM3). "
                    "For QASM3, PyZX may require conversion via Qiskit first."
                )
            }),
            500,
        )


# ---------------------------
# Entrypoint
# ---------------------------

if __name__ == "__main__":
    # Configure host/port via env if you like
    host = os.environ.get("HOST", "0.0.0.0")
    port = int(os.environ.get("PORT", "8085"))
    app.run(host=host, port=port)
