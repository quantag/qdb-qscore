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
