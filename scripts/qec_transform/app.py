import base64
import logging
import os
import traceback
from flask import Flask, request, jsonify
from flask_cors import CORS

import cudaq
import cudaq_qec
from qiskit import QuantumCircuit 

# Setup logging
LOG_DIR = "logs"
os.makedirs(LOG_DIR, exist_ok=True)
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger("qec_transform_app")

app = Flask(__name__)
CORS(app)

@app.route("/qec_transform", methods=["POST"])
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
                from qiskit import qasm3
                qc = qasm3.loads(qasm_str)
            except Exception as q3_err:
                raise ValueError(f"Failed to parse QASM with Qiskit. Ensure it's valid QASM. Error: {q3_err}")
        
        # ---------------------------------------------------------
        # cudaq-qec Implementation
        # 1. Select the QEC code based on the parameter
        if qec_code == "steane":
            code = cudaq_qec.get_code("steane")
        elif qec_code == "surface_d3":
            code = cudaq_qec.get_code("surface_code", distance=3)
        elif qec_code == "surface_d5":
            code = cudaq_qec.get_code("surface_code", distance=5)
        elif qec_code == "repetition_code":
            code = cudaq_qec.get_code("repetition_code")
        else:
            return jsonify({"error": f"Unknown QEC code: {qec_code}"}), 400

        # 2. Configure the noise model (required by DEM)
        if output_type == "dem" and noise_prob <= 0.0:
            noise_prob = 0.001

        noise_err_msg = ""
        try:
            noise_model = cudaq.NoiseModel()
            if noise_prob > 0.0:
                try:
                    depol = cudaq.DepolarizationChannel(noise_prob)
                except AttributeError:
                    depol = cudaq.BitFlipChannel(noise_prob)
                    
                for gate in ["h", "x", "y", "z", "mz", "measure", "s", "t"]:
                    try:
                        noise_model.add_all_qubit_channel(gate, depol)
                    except:
                        pass
        except Exception as e:
            noise_model = None
            noise_err_msg = str(e)
            logger.warning(f"Failed to initialize noise model: {e}")

        # 3. Generate the requested output
        if output_type == "dem":
            # Generate a Detector Error Model (DEM)
            try:
                op = cudaq_qec.qecrt.operation.prep0
                dem = cudaq_qec.dem_from_memory_circuit(code, op=op, numRounds=1, noise=noise_model)
                try:
                    num_det = dem.num_detectors() if callable(dem.num_detectors) else dem.num_detectors
                    num_obs = dem.num_observables() if callable(dem.num_observables) else dem.num_observables
                    num_err = dem.num_error_mechanisms() if callable(dem.num_error_mechanisms) else dem.num_error_mechanisms
                except:
                    num_det = num_obs = num_err = "Unknown"
                    
                transformed_content = f"// Detector Error Model (DEM) generated successfully!\n"
                transformed_content += f"// ----------------------------------------\n"
                transformed_content += f"// Number of Detectors: {num_det}\n"
                transformed_content += f"// Number of Observables: {num_obs}\n"
                transformed_content += f"// Number of Error Mechanisms: {num_err}\n"
                transformed_content += f"// ----------------------------------------\n"
                transformed_content += f"// The DEM matrices are ready for C++ or Python decoders.\n"
                transformed_content += f"// Note: cudaq_qec 0.8.0 exposes raw matrices instead of Stim strings.\n\n"
            except Exception as e:
                transformed_content = f"// DEM Generation Failed.\n"
                if noise_err_msg:
                    transformed_content += f"// Noise Model Initialization Error: {noise_err_msg}\n"
                transformed_content += f"// API Error Details:\n// {e}\n\n"
                transformed_content += qasm_str
        
        else:
            # Physical Circuit (QASM)
            try:
                num_data = code.get_num_data_qubits()
                num_anc_x = code.get_num_ancilla_x_qubits()
                num_anc_z = code.get_num_ancilla_z_qubits()
                num_anc = code.get_num_ancilla_qubits()
                num_x_stabs = code.get_num_x_stabilizers()
                num_z_stabs = code.get_num_z_stabilizers()
                
                transformed_content = f"// Physical Circuit Analysis using {qec_code.upper()}\n"
                transformed_content += f"// ----------------------------------------\n"
                transformed_content += f"// Data Qubits: {num_data}\n"
                transformed_content += f"// Ancilla Qubits: {num_anc} (X: {num_anc_x}, Z: {num_anc_z})\n"
                transformed_content += f"// Stabilizers: X-type: {num_x_stabs}, Z-type: {num_z_stabs}\n"
                transformed_content += f"// ----------------------------------------\n"
                transformed_content += f"// Note: cudaq_qec provides stabilization structures,\n"
                transformed_content += f"// rather than direct QASM transpilation in this version.\n"
                transformed_content += f"// Displaying logical circuit below:\n\n"
                transformed_content += qasm_str
            except Exception as e:
                logger.error(f"Failed to compile physical circuit analysis: {e}")
                transformed_content = f"// Physical Circuit Analysis Error: {e}\n\n" + qasm_str

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
    app.run(host="127.0.0.1", port=5042, debug=False)




