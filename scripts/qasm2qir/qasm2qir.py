from flask import Flask, request, jsonify
from flask_cors import CORS

import base64
import logging
import os
import re
import sys
import traceback

from qbraid_qir.qasm3 import qasm3_to_qir

from logging.handlers import RotatingFileHandler

def setup_logging(name="qasm2qir"):
    logger = logging.getLogger(name)
    logger.setLevel(logging.DEBUG)
    logger.propagate = False  # do not double-log via root

    log_dir = os.environ.get("QASM2QIR_LOG_DIR", "logs/")
    os.makedirs(log_dir, exist_ok=True)
    log_path = os.path.join(log_dir, "service.log")

    fmt = logging.Formatter(
        "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )

    # Console handler
    ch = logging.StreamHandler(sys.stdout)
    ch.setLevel(logging.INFO)
    ch.setFormatter(fmt)

    # Rotating file handler (10 MB per file, keep 5 backups)
    fh = RotatingFileHandler(
        log_path,
        maxBytes=10 * 1024 * 1024,
        backupCount=5,
        encoding="utf-8"
    )
    fh.setLevel(logging.DEBUG)
    fh.setFormatter(fmt)

    # Avoid adding handlers twice if gunicorn reloads workers
    if not logger.handlers:
        logger.addHandler(ch)
        logger.addHandler(fh)

    logger.info("Logging to %s", log_path)
    return logger

logger = setup_logging()


# --------------------------------------------------------------------
# Flask app
# --------------------------------------------------------------------
app = Flask(__name__)
CORS(app)


# --------------------------------------------------------------------
# Fixer: inline illegal initialize gate with reset
# --------------------------------------------------------------------
def maybe_inline_initialize_gate(qasm_text):
    """
    Your generator emits:
        gate initialize(...) q0..q6 { reset q0; ...; state_preparation(...) q0..q6; }
    OpenQASM forbids reset inside gate bodies.
    This function removes the gate and replaces the single call with:
        reset q[0..6]; state_preparation(...)
    Returns (new_text, did_fix).
    Non-fatal if pattern not present.
    """
    gate_re = re.compile(
        r"gate\s+initialize\([^)]*\)\s+q0,q1,q2,q3,q4,q5,q6\s*\{[^}]*\}\s*",
        re.S
    )
    call_re = re.compile(
        r"initialize\s*\(([^)]*)\)\s*q\[0\],q\[1\],q\[2\],q\[3\],q\[4\],q\[5\],q\[6\]\s*;",
        re.S
    )

    if not gate_re.search(qasm_text):
        return qasm_text, False

    text2, n_gates = gate_re.subn("", qasm_text)
    if n_gates != 1:
        logger.warning("Found %d initialize gates; not auto-inlining.", n_gates)
        return qasm_text, False

    m = call_re.search(text2)
    if not m:
        logger.warning("Initialize gate found but no initialize(...) call; not auto-inlining.")
        return qasm_text, False

    params = m.group(1).strip()

    replacement = (
        "reset q[0]; reset q[1]; reset q[2]; reset q[3]; "
        "reset q[4]; reset q[5]; reset q[6];\n"
        "state_preparation(" + params + ") q[0],q[1],q[2],q[3],q[4],q[5],q[6];"
    )

    text3, n_calls = call_re.subn(replacement, text2)
    if n_calls != 1:
        logger.warning("Expected 1 initialize call, found %d; not auto-inlining.", n_calls)
        return qasm_text, False

    return text3, True


# --------------------------------------------------------------------
# QASM2 -> QASM3 via Qiskit (loading from fixed string)
# --------------------------------------------------------------------
def qasm2_to_qasm3_from_text(qasm_text_fixed):
    """
    Convert QASM2 to valid QASM3:
      - load from fixed string (so reset-in-gate is already removed)
      - unroll to basis gates
      - dump QASM3
    """
    try:
        from qiskit import QuantumCircuit, transpile
    except Exception as e:
        raise RuntimeError(
            "Qiskit is required for OpenQASM 2.0 input. "
            "Install with: python -m pip install qiskit"
        ) from e

    qc = QuantumCircuit.from_qasm_str(qasm_text_fixed)

    qc_u = transpile(
        qc,
        basis_gates=[
            "id", "x", "y", "z", "h", "s", "sdg", "t", "tdg",
            "rx", "ry", "rz", "cx"
        ],
        optimization_level=0
    )

    try:
        qasm3_src = qc_u.qasm()
        if "OPENQASM 2.0" in qasm3_src:
            raise RuntimeError("Qiskit returned QASM2, forcing qasm3 dumps.")
    except Exception:
        from qiskit.qasm3 import dumps as qasm3_dumps
        qasm3_src = qasm3_dumps(qc_u)

    return qasm3_src


def ensure_qasm3(qasm_text_fixed):
    """
    If QASM2 detected -> convert to QASM3; else return as-is.
    Returns (qasm3_text, used_qiskit).
    """
    if "OPENQASM 2.0" in qasm_text_fixed:
        logger.info("Detected OpenQASM 2.0. Converting to OpenQASM 3 via Qiskit...")
        return qasm2_to_qasm3_from_text(qasm_text_fixed), True
    return qasm_text_fixed, False


# --------------------------------------------------------------------
# QIR output helpers (version compatible)
# --------------------------------------------------------------------
def module_to_bytes(module, fmt):
    """
    fmt:
      - "bitcode": return LLVM bitcode bytes
      - otherwise: return textual LLVM IR bytes
    Works with old/new qbraid-qir / pyqir APIs.
    """
    if fmt == "bitcode":
        if hasattr(module, "to_bitcode"):
            import tempfile
            with tempfile.NamedTemporaryFile(delete=False) as tmp:
                tmp_path = tmp.name
            try:
                module.to_bitcode(tmp_path)
                return open(tmp_path, "rb").read()
            finally:
                try:
                    os.remove(tmp_path)
                except Exception:
                    pass

        if hasattr(module, "bitcode"):
            return module.bitcode

        raise RuntimeError("QIR module has no to_bitcode() or bitcode attribute.")

    return str(module).encode("utf-8")


# --------------------------------------------------------------------
# Routes
# --------------------------------------------------------------------
@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": 0}), 200


@app.route("/qasm2qir", methods=["POST"])
def qasm2qir_route():
    logger.info("POST /qasm2qir")
    try:
        data = request.get_json(silent=True)
        if not data or "qasm" not in data:
            return jsonify({"status": 1, "error": "Missing 'qasm' in JSON"}), 400

        fmt = (data.get("format") or "text").lower()
        if fmt not in ["text", "bitcode"]:
            fmt = "text"

        # 1) decode base64
        qasm_bytes = base64.b64decode(data["qasm"])
        qasm_code = qasm_bytes.decode("utf-8", errors="replace")

        # 2) FIX BEFORE ANY QASM3 PARSE
        qasm_fixed, did_fix = maybe_inline_initialize_gate(qasm_code)
        if did_fix:
            logger.info("Applied initialize/reset inlining fix.")

        # 3) ensure QASM3 (QASM2 -> QASM3 if needed)
        qasm3_code, used_qiskit = ensure_qasm3(qasm_fixed)

        # 4) QASM3 -> QIR, with fallback unroll if direct parse fails
        try:
            qir_module = qasm3_to_qir(qasm3_code)
        except Exception as e1:
            if used_qiskit:
                raise
            logger.warning("Direct QASM3 parse failed, retrying via Qiskit unroll: %s", e1)
            qasm3_code = qasm2_to_qasm3_from_text(qasm_fixed)
            qir_module = qasm3_to_qir(qasm3_code)

        # 5) encode output
        qir_bytes = module_to_bytes(qir_module, fmt)
        qir_b64 = base64.b64encode(qir_bytes).decode("ascii")

        return jsonify({"status": 0, "format": fmt, "qir": qir_b64}), 200

    except Exception as e:
        tb = traceback.format_exc()
        logger.error("Exception:\n%s", tb)
        return jsonify({"status": 3, "error": str(e), "trace": tb}), 500


if __name__ == "__main__":
    logger.info("Starting qasm2qir service on port 5007")
    app.run(host="127.0.0.1", port=5007, debug=False)

