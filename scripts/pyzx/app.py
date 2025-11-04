import base64
import tempfile
import logging
import os
from datetime import datetime
from flask import Flask, request, jsonify
import pyzx as zx
from pyzx.drawing import draw
import matplotlib.pyplot as plt
from logging.handlers import RotatingFileHandler
from flask_cors import CORS
from qiskit import qasm3  # type: ignore
from qiskit.qasm3 import loads as q3loads  # type: ignore

# ---------------------------------------------------------------------
# Setup logging
# ---------------------------------------------------------------------
LOG_DIR = "logs"
os.makedirs(LOG_DIR, exist_ok=True)

log_file = os.path.join(LOG_DIR, "app.log")

logger = logging.getLogger("pyzx_app")
logger.setLevel(logging.DEBUG)

# Rotating file handler (max 5 MB per file, 5 backups)
file_handler = RotatingFileHandler(log_file, maxBytes=5 * 1024 * 1024, backupCount=5)
file_handler.setLevel(logging.DEBUG)

# Console handler
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO)

# Formatter
formatter = logging.Formatter(
    "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
file_handler.setFormatter(formatter)
console_handler.setFormatter(formatter)

logger.addHandler(file_handler)
logger.addHandler(console_handler)

# ---------------------------------------------------------------------
# Flask setup
# ---------------------------------------------------------------------
app = Flask(__name__)
CORS(app)

def _timestamp() -> str:
    return datetime.now().strftime("%Y-%m-%d_%H-%M-%S")

def _save_qasm(content: str, prefix: str) -> str:
    """Save QASM content to logs folder with timestamp."""
    filename = os.path.join(LOG_DIR, f"{prefix}_{_timestamp()}.qasm")
    with open(filename, "w", encoding="utf-8") as f:
        f.write(content)
    logger.debug(f"Saved QASM file: {filename}")
    return filename

@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": 0}), 200

# -------------------------- /rend endpoint ---------------------------
# Paste this block AFTER `app = Flask(__name__)` and your logger setup.


def _convert_to_qasm(src_str: str, src_type: int) -> str:
    """
    Convert input text to OpenQASM 2.0 string, based on src_type:
      0 = QASM 2 (pass-through)
      1 = QASM 3 (requires qiskit)
      2 = Qiskit Python (NOT SUPPORTED for safety)
      3 = pyTKET Python (NOT SUPPORTED for safety)
    Returns QASM 2 string on success; raises ValueError on unsupported/failed conversion.
    """
    if src_type == 0:
        # Heuristic check only; do not block if header is missing.
        if ("OPENQASM 2" not in src_str) and ("OPENQASM 2.0" not in src_str):
            try:
                logger.warning("Type 0 selected but input may not be QASM 2.")
            except Exception:
                pass
        return src_str

    if src_type == 1:
        # QASM 3 -> QuantumCircuit -> qasm() (QASM2)
        try:
            # Prefer qiskit>=2 with qasm3 module
            try:
                qc = qasm3.loads(src_str)
            except Exception:
                # Fallback import path used by some versions
                qc = q3loads(src_str)

            # qasm3.loads may return QuantumCircuit or list[QuantumCircuit]
            try:
                from qiskit import QuantumCircuit  # type: ignore
            except Exception as e:
                raise ValueError("Qiskit not available for QASM3 conversion") from e

            if isinstance(qc, list):
                if not qc:
                    raise ValueError("Empty circuit list parsed from QASM 3")
                first = qc[0]
                if not isinstance(first, QuantumCircuit):
                    raise ValueError("Parsed object is not a QuantumCircuit")
                qc = first
            elif not isinstance(qc, QuantumCircuit):
                raise ValueError("Parsed object is not a QuantumCircuit")

            # Export to OpenQASM 2
            return qc.qasm()
        except Exception as e:
            raise ValueError(f"QASM 3 conversion failed: {e}")

    if src_type in (2, 3):
        # Intentionally do not execute arbitrary Python sources.
        raise ValueError(
            "Types 2 (Qiskit Python) and 3 (pyTKET Python) are not supported here. "
            "Please submit QASM 2 (type=0) or QASM 3 (type=1)."
        )

    raise ValueError("Unknown 'type' value. Use 0 (qasm2) or 1 (qasm3).")

def _timestamp() -> str:
    return datetime.now().strftime("%Y-%m-%d_%H-%M-%S")


def _render_qasm_to_png_b64(qasm_text: str) -> str:
    """
    Render QASM text exactly as /render does: via zx.draw() and a temporary PNG.
    Returns base64-encoded PNG bytes.
    """

    # Build and draw circuit (same as /render)
    circuit = zx.Circuit.from_qasm(qasm_text)
    graph = circuit.to_graph()
    fig = draw(graph)
    fig.set_size_inches(fig.get_size_inches() * 2)

    # Save to temp PNG
    with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
        fig.savefig(tmp.name, format="png", bbox_inches="tight")
        tmp.seek(0)
        image_bytes = tmp.read()

    plt.close(fig)
    return base64.b64encode(image_bytes).decode("utf-8")

@app.route("/rend", methods=["POST"])
def rend():
    """
    Accepts JSON:
      {
        "src": "<base64-encoded source>",
        "type": 0|1|2|3
      }
    Converts to QASM 2 where possible, then renders like /render.
    Response:
      { "image": "<base64-png>", "qasm": "<base64-qasm2>" }
    """
    try:
        data = request.get_json(silent=True) or {}
        src_b64 = data.get("src")
        src_type = data.get("type")
        logger.info("/rend called: type=%s, src_length=%s",src_type,len(src_b64) if src_b64 else 0 )

        if src_b64 is None or src_type is None:
            logger.warning("/rend failed: Missing 'src' or 'type' 400")
            return jsonify({"error": "Missing 'src' or 'type'"}), 400

        try:
            src_bytes = base64.b64decode(src_b64, validate=True)
        except Exception:
            logger.warning("/rend failed: Invalid base64 in 'src' 400")
            return jsonify({"error": "Invalid base64 in 'src'"}), 400

        try:
            qasm_text = _convert_to_qasm(src_bytes.decode("utf-8"), int(src_type))
        except ValueError as ve:
            logger.warning("/rend failed: _convert_to_qasm failed 400")
            return jsonify({"error": str(ve)}), 400

        # Render with PyZX (same style as /render)
        png_b64 = _render_qasm_to_png_b64(qasm_text)

        # Optionally persist QASM to disk (comment out if not desired)
        try:
            os.makedirs("qasm_in", exist_ok=True)
            fname = os.path.join("qasm_in", f"rend_{_timestamp()}.qasm")
            with open(fname, "w", encoding="utf-8") as f:
                f.write(qasm_text)
            try:
                logger.info("Saved QASM to %s", fname)
            except Exception:
                pass
        except Exception:
            # Non-fatal
            pass

        return jsonify({
            "image": png_b64,
            "qasm": base64.b64encode(qasm_text.encode("utf-8")).decode("utf-8")
        })

    except Exception as e:
        try:
            logger.exception("Unexpected error during /rend")
        except Exception:
            pass
        return jsonify({"error": str(e)}), 500
# ------------------------ end /rend endpoint -------------------------


# ---------------------------------------------------------------------
# /render endpoint
# ---------------------------------------------------------------------
@app.route("/render", methods=["POST"])
def render_pyzx():
    try:
        data = request.json
        qasm_b64 = data.get("qasm")
        if not qasm_b64:
            return jsonify({"error": "Missing 'qasm' in request"}), 400

        qasm_str = base64.b64decode(qasm_b64).decode("utf-8")
        input_file = _save_qasm(qasm_str, "input")

        logger.info(f"/render called with {input_file}")

        # Load and visualize circuit
        circuit = zx.Circuit.from_qasm(qasm_str)
        graph = circuit.to_graph()

        fig = draw(graph)
        fig.set_size_inches(fig.get_size_inches() * 2)
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
            fig.savefig(tmp.name, format="png", bbox_inches="tight")
            tmp.seek(0)
            image_bytes = tmp.read()

        image_b64 = base64.b64encode(image_bytes).decode("utf-8")
        logger.info(f"/render completed successfully for {input_file}")
        return jsonify({"image": image_b64})

    except Exception as e:
        logger.exception("Unexpected error in /render")
        return jsonify({"error": str(e)}), 500

# ---------------------------------------------------------------------
# /optimize endpoint
# ---------------------------------------------------------------------
@app.route("/optimize", methods=["POST"])
def optimize_qasm():
    try:
        data = request.json
        qasm_b64 = data.get("qasm")
        if not qasm_b64:
            return jsonify({"error": "Missing 'qasm' in request"}), 400

        qasm_str = base64.b64decode(qasm_b64).decode("utf-8")
        input_file = _save_qasm(qasm_str, "input")

        logger.info(f"/optimize called with {input_file}")

        # Load and simplify circuit
        circuit = zx.Circuit.from_qasm(qasm_str)
        graph = circuit.to_graph()
        zx.simplify.full_reduce(graph)

        optimized_circuit = zx.extract.extract_circuit(graph)
        optimized_qasm = optimized_circuit.to_qasm()
        optimized_file = _save_qasm(optimized_qasm, "optimized")

        logger.info(
            f"Optimization done: {input_file} -> {optimized_file}"
        )

        optimized_b64 = base64.b64encode(optimized_qasm.encode("utf-8")).decode("utf-8")
        return jsonify({"qasm": optimized_b64})

    except Exception as e:
        logger.exception("Unexpected error during /optimize")
        return jsonify({"error": str(e)}), 500

# ---------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------
if __name__ == "__main__":
    logger.info("Starting PyZX Flask server on port 5037")
    app.run(port=5037)
