import base64
import tempfile
import logging
from flask import Flask, request, jsonify
import pyzx as zx
from pyzx.drawing import draw

import matplotlib.pyplot as plt

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.DEBUG)

app = Flask(__name__)

@app.route('/render', methods=['POST'])
def render_pyzx():
    try:
        data = request.json
        qasm_b64 = data.get('qasm')
        if not qasm_b64:
            return jsonify({"error": "Missing 'qasm' in request"}), 400

        qasm_str = base64.b64decode(qasm_b64).decode('utf-8')

        # Step 1: Load circuit and graph
        circuit = zx.Circuit.from_qasm(qasm_str)
        graph = circuit.to_graph()

        # Step 2: Optional simplification
        # zx.simplify.full_reduce(graph)

        # Step 3: Draw and save manually
        fig = draw(graph)  # returns matplotlib Figure
        fig.set_size_inches(fig.get_size_inches() * 2)
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
            fig.savefig(tmp.name, format="png", bbox_inches="tight")
            tmp.seek(0)
            image_bytes = tmp.read()

        image_b64 = base64.b64encode(image_bytes).decode('utf-8')
        return jsonify({"image": image_b64})

    except Exception as e:
        logger.exception("Unexpected error")
        return jsonify({"error": str(e)}), 500


@app.route('/optimize', methods=['POST'])
def optimize_qasm():
    try:
        data = request.json
        qasm_b64 = data.get('qasm')
        if not qasm_b64:
            return jsonify({"error": "Missing 'qasm' in request"}), 400

        # Decode base64 QASM
        qasm_str = base64.b64decode(qasm_b64).decode('utf-8')

        # Load circuit into PyZX
        circuit = zx.Circuit.from_qasm(qasm_str)

        # Convert to ZX-graph
        graph = circuit.to_graph()

        # Run simplification
        zx.simplify.full_reduce(graph)

        # Extract optimized circuit
        optimized_circuit = zx.extract.extract_circuit(graph)

        # Export back to QASM
        optimized_qasm = optimized_circuit.to_qasm()

        # Encode QASM to base64
        optimized_b64 = base64.b64encode(optimized_qasm.encode('utf-8')).decode('utf-8')

        return jsonify({"qasm": optimized_b64})

    except Exception as e:
        logger.exception("Unexpected error during optimization")
        return jsonify({"error": str(e)}), 500


if __name__ == '__main__':
    app.run(port=5037)
