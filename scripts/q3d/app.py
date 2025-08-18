#!/usr/bin/env python3
# app.py  Flask API: QASM (base64) - backend -> visualization JSON
#
# Run:
#   python app.py
# Then POST:
#   curl -X POST http://127.0.0.1:5036/transpile \
#     -H "Content-Type: application/json" \
#     -d '{"qasm_b64":"<base64 of your .qasm>","backend":"ibm_brisbane","opt":3}'
#
# Response: JSON with keys: meta, hardware{nodes,edges}, mapping{virtual_to_physical}, circuit{gates}

import base64
import json
import math
import os
import traceback
from datetime import datetime
from typing import Dict, Any

from flask import Flask, request, jsonify

from qiskit import QuantumCircuit, transpile
from qiskit.converters import circuit_to_dag
from flask_cors import CORS
from pathlib import Path

# Optional QASM3 parser (Qiskit 2.x provides qiskit.qasm3)
try:
    import qiskit.qasm3 as qasm3_mod
except Exception:
    qasm3_mod = None

# IBM Runtime
from qiskit_ibm_runtime import QiskitRuntimeService


# ---------------------------
# Helpers (backend + geometry)
# ---------------------------
SAMPLES_DIR = Path(os.getcwd()) / "qasm"
SAMPLES_DIR = SAMPLES_DIR.resolve()
#print(SAMPLES_DIR)
#Path(os.environ.get("QASM_SAMPLES_DIR", Path(__file__).parent / "qasm")).resolve()

def _list_qasm_files():
    """Return list of dicts: [{"name","size_bytes","modified"}] from SAMPLES_DIR."""
    files = []
    if not SAMPLES_DIR.exists():
        print("samples folder not exists")
        return files

    print("samples folder exists")
    for p in SAMPLES_DIR.glob("*.qasm"):
        print(p)
        try:
            st = p.stat()
            files.append({
                "name": p.name,
                "size_bytes": st.st_size
            })
        except Exception as e:
            # skip unreadable files
            print(f"Error processing {p}: {e}")
            pass
    # sort by name for stable UI
    files.sort(key=lambda x: x["name"])
    return files


def _resolve_sample_path(name: str) -> Path:
    """
    Safely resolve a file path under SAMPLES_DIR.
    Only allow *.qasm, disallow path traversal.
    """
    if not name or not name.lower().endswith(".qasm"):
        raise ValueError("Only .qasm filenames are allowed.")
    # Prevent traversal
    candidate = (SAMPLES_DIR / os.path.basename(name)).resolve()
    try:
        # Python 3.9+: candidate.is_relative_to(SAMPLES_DIR)
        candidate.relative_to(SAMPLES_DIR)
    except Exception:
        raise ValueError("Invalid filename or path.")
    if not candidate.exists() or not candidate.is_file():
        raise FileNotFoundError(f"Sample not found: {name}")
    return candidate



def choose_backend(service: QiskitRuntimeService, name: str):
    if name:
        return service.backend(name)
    # fallback: any non-simulator backend
    cands = [b for b in service.backends() if not getattr(b.configuration(), "simulator", False)]
    if not cands:
        raise RuntimeError("No hardware backends found for this account.")
    return cands[0]


def get_coupling_edges(backend):
    """Return list of (u,v) physical qubit ids."""
    try:
        cm = backend.target.build_coupling_map()
        return [(int(u), int(v)) for (u, v) in cm.get_edges()]
    except Exception:
        pass
    cm = getattr(backend, "coupling_map", None)
    if cm is None:
        raise RuntimeError("Backend has no coupling map.")
    return [(int(u), int(v)) for (u, v) in cm.get_edges()]


def get_qubit_coords(backend, num_qubits: int):
    """Return [(x,y,z=0)] for each physical qubit; fallback to circle."""
    coords = None
    try:
        cfg = backend.configuration()
        coords = getattr(cfg, "qubit_coordinates", None)
    except Exception:
        coords = None

    if coords and len(coords) == num_qubits:
        return [(float(x), float(y), 0.0) for (x, y) in coords]

    # fallback: circle
    R = 10.0
    out = []
    for i in range(num_qubits):
        ang = 2.0 * math.pi * (i / max(1, num_qubits))
        out.append((R * math.cos(ang), R * math.sin(ang), 0.0))
    return out


# ---------------------------
# QASM loading
# ---------------------------

def load_circuit_from_qasm_str(src: str) -> QuantumCircuit:
    """
    Try OpenQASM 3 via qiskit.qasm3, then QASM 2 via QuantumCircuit.from_qasm_str.
    """
    # QASM 3
    if qasm3_mod is not None:
        try:
            return qasm3_mod.loads(src)
        except Exception:
            pass
    # QASM 2
    try:
        return QuantumCircuit.from_qasm_str(src)
    except Exception as e:
        raise RuntimeError("Failed to parse QASM (tried v3 then v2).") from e


# ---------------------------
# Mapping + gate layering
# ---------------------------

def build_v2p_mapping(tcirc: QuantumCircuit, original: QuantumCircuit) -> Dict[int, int]:
    """
    Robust virtual->physical mapping for Qiskit 2.1+.
    Prefer tcirc.layout.initial_layout when available; fall back as needed.
    Returns {virtual_index: physical_index}.
    """
    v2p: Dict[int, int] = {}
    layout = getattr(tcirc, "layout", None)
    if layout is None:
        return v2p

    L = getattr(layout, "initial_layout", layout)

    # We try a few access styles for compatibility across minor versions:
    # 1) dict-like items() / to_dict()
    items = None
    for attr in ("items", "to_dict"):
        if hasattr(L, attr):
            try:
                obj = getattr(L, attr)()
                items = list(obj.items()) if isinstance(obj, dict) else list(obj)
                break
            except Exception:
                pass

    # 2) older API
    if items is None and hasattr(L, "get_virtual_bits"):
        try:
            items = list(L.get_virtual_bits().items())
        except Exception:
            items = None

    # 3) last resort: treat as dict-like directly
    if items is None:
        try:
            items = list(L.items())
        except Exception:
            items = None

    if not items:
        return v2p

    for vq, p in items:
        # virtual index from the ORIGINAL circuit
        try:
            v_idx = int(original.find_bit(vq).index)
        except Exception:
            v_idx = getattr(vq, "index", None)
            if v_idx is None:
                continue
            v_idx = int(v_idx)

        # physical index can be int, Bit, or Qubit
        if isinstance(p, int):
            p_idx = p
        else:
            p_idx = getattr(p, "index", None)
            if p_idx is None:
                try:
                    p_idx = int(tcirc.find_bit(p).index)
                except Exception:
                    continue
        v2p[v_idx] = int(p_idx)

    return v2p


def layerize_transpiled(tcirc: QuantumCircuit):
    """
    Build gate list with PHYSICAL qubit indices and layer times from the transpiled circuit.
    Uses DAG layers as time steps and tcirc.find_bit(q).index which is physical after mapping.
    Returns list of dicts: {id, name, qargs:[phys_ids], params:[], t:layer}
    """
    dag = circuit_to_dag(tcirc)
    layer_index = 0
    gates = []
    gid = 0

    for layer in dag.layers():
        ops = [op for op in layer["graph"].op_nodes() if op.name != "barrier"]
        if not ops:
            layer_index += 1
            continue
        for op in ops:
            q_indices = [int(tcirc.find_bit(q).index) for q in op.qargs]
            params = []
            if hasattr(op, "op") and hasattr(op.op, "params"):
                try:
                    params = [float(p) for p in op.op.params]
                except Exception:
                    params = []
            gates.append({
                "id": gid,
                "name": op.name,
                "qargs": q_indices,
                "params": params,
                "t": layer_index
            })
            gid += 1
        layer_index += 1

    return gates


# ---------------------------
# Flask app
# ---------------------------

app = Flask(__name__)

CORS(
    app,
    resources={r"/*": {"origins": [
        "http://127.0.0.1:8000",
        "http://localhost:8000",
        "http://127.0.0.1",
        "http://localhost",
        "https://quantum.quantag-it.com",
        "https://quantag-it.com"   
     ]}},
    supports_credentials=False,  # keep False unless you actually need cookies
    methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Content-Type"]
)


@app.route("/", methods=["GET"])
def health():
    return jsonify({"ok": True, "service": "qasm->cudaq-viz (Qiskit/IBM)", "time": datetime.utcnow().isoformat() + "Z"})


@app.route("/list_backends", methods=["GET"])
def list_backends():
    try:
        service = QiskitRuntimeService()
        backends_info = []

        for b in service.backends():
            try:
                config = b.configuration()
                status = b.status()
                backends_info.append({
                    "name": b.name,
                    "num_qubits": config.num_qubits,
                    "simulator": config.simulator,
                    "operational": getattr(status, "operational", None),
                    "pending_jobs": getattr(status, "pending_jobs", None),
                    "backend_version": getattr(config, "backend_version", None),
                })
            except Exception as e:
                backends_info.append({"name": b.name, "error": str(e)})

        return jsonify({"backends": backends_info})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/samples", methods=["GET"])
def list_samples():
    """
    List available sample .qasm files from SAMPLES_DIR.
    Returns: { "dir": "<path>", "files": [ {name, size_bytes, modified}, ... ] }
    """
    files = _list_qasm_files()
    return jsonify({
#        "dir": str(SAMPLES_DIR),
        "files": files
    })


@app.route("/samples/<name>", methods=["GET"])
def get_sample(name: str):
    """
    Return a single sample file as base64.
    Optional query: ?format=raw -> return text/plain raw QASM instead of JSON/base64
    """
    try:
        path = _resolve_sample_path(name)
    except (ValueError, FileNotFoundError) as e:
        return jsonify({"error": str(e)}), 400

    fmt = (request.args.get("format") or "base64").lower()

    try:
        if fmt == "raw":
            # Return raw QASM text
            text = path.read_text(encoding="utf-8")
            return app.response_class(
                response=text,
                status=200,
                mimetype="text/plain; charset=utf-8"
            )
        else:
            # Default: return base64 JSON
            data_b64 = base64.b64encode(path.read_bytes()).decode("ascii")
            return jsonify({
                "name": path.name,
                "qasm_b64": data_b64,
                "size_bytes": path.stat().st_size
            })
    except Exception as e:
        return jsonify({"error": f"Failed to read sample: {e}"}), 500



@app.route("/transpile", methods=["POST"])
def transpile_endpoint():
    """
    JSON body:
      {
        "qasm_b64": "<base64 string>",  # required
        "backend": "ibm_brisbane",      # required
        "opt": 3                        # optional, default 3
      }
    Returns:
      visualization JSON (meta, hardware, mapping, circuit) or {error: "..."} with 400/500.
    """
    try:
        payload = request.get_json(force=True, silent=False)
        if not payload:
            return jsonify({"error": "No JSON body"}), 400

        qasm_b64 = payload.get("qasm_b64")
        backend_name = payload.get("backend")
        opt = int(payload.get("opt", 3))

        if not qasm_b64 or not backend_name:
            return jsonify({"error": "Missing required fields: qasm_b64, backend"}), 400

        try:
            qasm_src = base64.b64decode(qasm_b64).decode("utf-8")
        except Exception as e:
            return jsonify({"error": f"Invalid base64 for qasm_b64: {e}"}), 400

        # Build circuit
        circ = load_circuit_from_qasm_str(qasm_src)

        # Connect to IBM Quantum
        service = QiskitRuntimeService()
        backend = choose_backend(service, backend_name)
        num_qubits = int(backend.configuration().num_qubits)

        # Transpile
        tcirc = transpile(
            circ,
            backend=backend,
            optimization_level=opt,
            layout_method="sabre",
            routing_method="sabre"
        )

        # Extract data
        edges = get_coupling_edges(backend)                 # [(u,v)]
        coords = get_qubit_coords(backend, num_qubits)      # [(x,y,z)]
        v2p = build_v2p_mapping(tcirc, circ)                # {virt:phys}
        gates = layerize_transpiled(tcirc)                  # [{id,name,qargs,t,params}]

        depth_layers = (max((g["t"] for g in gates), default=-1) + 1) if gates else 0

        data: Dict[str, Any] = {
            "meta": {
                "generated_at": datetime.utcnow().isoformat() + "Z",
                "backend_name": backend.name,
                "backend_version": getattr(backend, "version", None),
                "num_qubits": num_qubits,
                "original_circuit_qubits": circ.num_qubits,
                "transpiled_depth_layers": depth_layers,
                "optimization_level": opt
            },
            "hardware": {
                "nodes": [{"id": i, "x": coords[i][0], "y": coords[i][1], "z": coords[i][2]} for i in range(num_qubits)],
                "edges": [{"source": int(u), "target": int(v)} for (u, v) in edges]
            },
            "mapping": {
                "virtual_to_physical": v2p
            },
            "circuit": {
                "gates": gates  # qargs are PHYSICAL ids
            }
        }

        return app.response_class(
            response=json.dumps(data, indent=2),
            status=200,
            mimetype="application/json"
        )

    except Exception as e:
        tb = traceback.format_exc(limit=5)
        return jsonify({"error": str(e), "trace": tb}), 500


if __name__ == "__main__":
    # You can set host="0.0.0.0" to expose on your LAN
    app.run(host="127.0.0.1", port=5036, debug=False)
