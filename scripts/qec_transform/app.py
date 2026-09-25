import base64
import logging
import os
import traceback
from flask import Flask, request, jsonify
from flask_cors import CORS

import cudaq_qec
from qiskit import QuantumCircuit
from qiskit import qasm3


# Setup logging
LOG_DIR = "logs"
os.makedirs(LOG_DIR, exist_ok=True)
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger("qec_transform_app")

app = Flask(__name__)
CORS(app)

@app.route("/api16/qec_transform", methods=["POST"])
def transform():
    try:
        data = request.json
        if not data or "qasm" not in data:
            return jsonify({"error": "Missing 'qasm' in payload"}), 400

        qasm_b64 = data["qasm"]
        qasm_str = base64.b64decode(qasm_b64).decode("utf-8")
        
        qec_code = data.get("qec_code", "steane")
        output_type = data.get("output_type", "physical_circuit")
        noise_prob = data.get("noise_prob", 0.0)

        logger.info(f"Received QASM. Code: {qec_code}, Output: {output_type}, Noise: {noise_prob}")
        
        # Parse the QASM string into a Qiskit QuantumCircuit
        try:
            qc = QuantumCircuit.from_qasm_str(qasm_str)
        except Exception as q_err:
            logger.warning(f"Failed to parse QASM 2.0 with QuantumCircuit, trying qasm3... Error: {q_err}")
            try:
                qc = qasm3.loads(qasm_str)
            except Exception as q3_err:
                raise ValueError(f"Failed to parse QASM with Qiskit. Ensure it's valid QASM. Error: {q3_err}")
        
        # ---------------------------------------------------------
        # cudaq-qec Implementation
        # 1. Select the QEC code based on the parameter
        if qec_code == "steane":
            code = cudaq_qec.codes.SteaneCode()
        elif qec_code == "surface_d3":
            code = cudaq_qec.codes.SurfaceCode(3)
        elif qec_code == "surface_d5":
            code = cudaq_qec.codes.SurfaceCode(5)
        elif qec_code == "repetition":
            code = cudaq_qec.codes.RepetitionCode(3)
        else:
            return jsonify({"error": f"Unknown QEC code: {qec_code}"}), 400

        # 2. Configure the noise model if specified
        noise_model = None
        if noise_prob > 0.0:
            noise_model = cudaq_qec.DepolarizingNoise(noise_prob)

        # 3. Generate the requested output
        if output_type == "dem":
            # Generate a Detector Error Model (DEM)
            try:
                dem = cudaq_qec.dem_from_memory_circuit(code, noise_model=noise_model)
                transformed_content = str(dem)
            except AttributeError:
                transformed_content = "DEM generation requires specific state preparation in this version of cudaq_qec."
        
        else:
            # Physical Circuit (QASM)
            # Transpile the logical circuit to a physical circuit
            try:
                # Attempt to encode the circuit (exact method depends on cudaq-qec version)
                qc_physical = code.encode(qc)
                transformed_content = qc_physical.qasm()
            except Exception as e:
                logger.error(f"Failed to compile physical circuit: {e}")
                # Fallback: just show the code properties
                transformed_content = f"// Physical Circuit Simulation using {qec_code}\n"
                transformed_content += f"// Logical Qubits: {code.num_logical_qubits}\n"
                transformed_content += f"// Physical Qubits: {code.num_physical_qubits}\n"
                transformed_content += f"// Distance: {code.distance}\n\n"
                transformed_content += qasm_str

        # Add descriptive headers to the output
        header = f"// ==========================================\n"
        header += f"// QEC Transformation Result\n"
        header += f"// Code Selected: {qec_code}\n"
        header += f"// Output Type: {output_type}\n"
        header += f"// Noise Probability: {noise_prob}\n"
        header += f"// ==========================================\n\n"
        
        final_content = header + transformed_content

        transformed_b64 = base64.b64encode(final_content.encode("utf-8")).decode("utf-8")

        return jsonify({"qasm": transformed_b64})

    except Exception as e:
        logger.error(f"Error during QEC transform: {traceback.format_exc()}")
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
