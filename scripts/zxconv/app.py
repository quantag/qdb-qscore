import base64
import json
import os
import traceback
from typing import Any, Dict, Tuple

from flask import Flask, jsonify, request
from flask_cors import CORS
import logging
from logging.handlers import RotatingFileHandler

# Optional Qiskit fallback for QASM3
try:
    from qiskit import QuantumCircuit
    _HAS_QISKIT = True
except Exception:
    _HAS_QISKIT = False

import pyzx as zx

app = Flask(__name__)
CORS(app)

# ===============================================================
# LOGGING SETUP
# ===============================================================

LOG_DIR = os.environ.get("LOG_DIR", "./logs")
os.makedirs(LOG_DIR, exist_ok=True)

log_file = os.path.join(LOG_DIR, "mbqc_service.log")

# Create rotating file handler (10 MB per file, 5 backups)
file_handler = RotatingFileHandler(log_file, maxBytes=10 * 1024 * 1024, backupCount=5)
console_handler = logging.StreamHandler()

formatter = logging.Formatter(
    fmt="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
file_handler.setFormatter(formatter)
console_handler.setFormatter(formatter)

logger = logging.getLogger("MBQCService")
logger.setLevel(logging.INFO)
logger.addHandler(file_handler)
logger.addHandler(console_handler)

# ===============================================================
# UTILS
# ===============================================================

def _decode_b64_src(src_b64: str) -> str:
    try:
        return base64.b64decode(src_b64).decode("utf-8")
    except Exception as e:
        raise ValueError(f"Failed to decode base64 'src': {e}")

def _load_pyzx_circuit_from_qasm(qasm_str: str) -> zx.Circuit:
    """
    Load a PyZX circuit from OpenQASM text.
    - Prefer native PyZX (QASM2).
    - Else parse with Qiskit (QASM2/3) and export *to QASM2*:
        * Qiskit >= 1.0:   qiskit.qasm2.dumps(circuit)
        * Qiskit <= 0.45:  circuit.qasm()
    """
    # 1) Try native PyZX (OpenQASM 2)
    try:
        return zx.Circuit.from_qasm(qasm_str)
    except Exception:
        pass

    if not _HAS_QISKIT:
        raise ValueError("PyZX parse failed and Qiskit is not available.")

    # 2) Parse with Qiskit (handles QASM2 and QASM3 input)
    try:
        qc = QuantumCircuit.from_qasm_str(qasm_str)
    except Exception as e:
        raise RuntimeError(f"Qiskit failed to parse QASM input: {e}")

    # 3) Export to OpenQASM 2 text
    qasm2_text = None

    # New path (Qiskit >= 1.x): qasm2.dumps
    try:
        # Import inside the function to avoid hard dependency if not present
        from qiskit.qasm2 import dumps as qasm2_dumps  # type: ignore
        qasm2_text = qasm2_dumps(qc)
    except Exception:
        # Old path (Qiskit <= 0.45): circuit.qasm()
        try:
            qasm2_text = qc.qasm()
        except Exception as e_old:
            # Neither exporter is available -> instruct to install qiskit-qasm2
            raise RuntimeError(
                "Qiskit fallback conversion failed: no QASM2 exporter available. "
                "Install the Qiskit QASM2 exporter with:\n"
                "    pip install qiskit-qasm2\n"
                f"Details: qasm2.dumps missing, and circuit.qasm() unavailable ({e_old})"
            )

    # 4) Feed the QASM2 text to PyZX
    try:
        return zx.Circuit.from_qasm(qasm2_text)
    except Exception as e:
        raise RuntimeError(f"PyZX failed to parse exported QASM2: {e}")



def _zx_graph_from_circuit(circ: zx.Circuit) -> zx.graph.graph_s.GraphS:
    return circ.to_graph()

def _serialize_zx_graph(g: zx.graph.graph_s.GraphS) -> Dict[str, Any]:
    verts = []
    for v in g.vertices():
        data = {
            "id": int(v),
            "type": str(g.type(v)),
            "phase": float(g.phase(v)) if g.phase(v) is not None else 0.0,
        }
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
    edges = []
    for e in g.edges():
        try:
            s, t = g.edge_st(e)
        except Exception:
            s, t = e
        edges.append([int(s), int(t)])
    return {"vertices": verts, "edges": edges}

def _try_extract_mbqc(g: zx.graph.graph_s.GraphS) -> Dict[str, Any]:
    try:
        flow = zx.flow.extract_flow(g)
    except Exception as e:
        return {
            "supported": False,
            "notes": f"Flow extraction failed: {e}",
        }

    order = []
    try:
        order = list(flow.order)
    except Exception:
        try:
            order = list(getattr(flow, "measurement_order", []))
        except Exception:
            pass

    feedforward = {}
    try:
        for k, vs in getattr(flow, "successors", {}).items():
            feedforward[str(int(k))] = [int(x) for x in vs]
    except Exception:
        pass

    measurements = []
    try:
        for v in order:
            vtype = str(g.type(v))
            angle = float(g.phase(v)) if g.phase(v) is not None else 0.0
            if vtype.upper().startswith("Z"):
                basis = "X-basis (from Z-spider)"
            elif vtype.upper().startswith("X"):
                basis = "Z-basis (from X-spider)"
            else:
                basis = vtype
            measurements.append({"v": int(v), "basis": basis, "angle": angle})
    except Exception:
        pass

    return {
        "supported": True,
        "order": [int(v) for v in order],
        "measurements": measurements,
        "feedforward": feedforward,
        "notes": "MBQC pattern extracted using PyZX flow (best effort).",
    }

# ===============================================================
# ROUTES
# ===============================================================

@app.before_request
def log_request_info():
    if request.path == "/health":
        return
    logger.info(f"Incoming {request.method} {request.path} from {request.remote_addr}")

@app.after_request
def log_response_info(response):
    if request.path == "/health":
        return response
    logger.info(f"Response {response.status_code} for {request.path}")
    return response

@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": 0}), 200

@app.route("/translate", methods=["POST"])
def translate():
    try:
        data = request.get_json(force=True, silent=False) or {}
        src_b64 = data.get("src", "")
        output_mode = data.get("output", "all").lower()

        if not src_b64:
            logger.warning("Missing 'src' field in request.")
            return jsonify({"error": "Missing 'src' (base64-encoded QASM)."}), 400

        qasm = _decode_b64_src(src_b64)
        logger.info(f"Decoded QASM input ({len(qasm)} chars)")

        circ = _load_pyzx_circuit_from_qasm(qasm)
        g = _zx_graph_from_circuit(circ)
        zx_json = _serialize_zx_graph(g)

        resp = {"zx_graph": zx_json}

        if output_mode in ("all", "mbqc"):
            mbqc = _try_extract_mbqc(g)
            resp["mbqc_pattern"] = mbqc

        logger.info("Translation completed successfully.")
        return jsonify(resp), 200

    except Exception as e:
        tb = traceback.format_exc()
        logger.error(f"Error during /translate: {e}\n{tb}")
        return jsonify({
            "error": str(e),
            "traceback": tb,
        }), 500

@app.route("/version", methods=["GET"])
def version():
    lib_versions = {
        "pyzx": getattr(zx, "__version__", "unknown"),
        "qiskit_available": _HAS_QISKIT,
    }
    return jsonify(lib_versions), 200

# ===============================================================
# MAIN ENTRY
# ===============================================================

if __name__ == "__main__":
    host = os.environ.get("HOST", "0.0.0.0")
    port = int(os.environ.get("PORT", "8085"))
    logger.info(f"Starting MBQC microservice on {host}:{port}")
    app.run(host=host, port=port)
