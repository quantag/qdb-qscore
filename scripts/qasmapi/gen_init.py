from flask import Flask, request, jsonify
import numpy as np
import base64
import traceback
from qiskit import QuantumCircuit
from qiskit.circuit.library import Initialize
from qiskit.qasm2 import dumps
from math import ceil, log2

app = Flask(__name__)

@app.route("/gen_init_qasm", methods=["POST"])
def gen_init_qasm():
    try:
        data = request.get_json()
        b64 = data.get("data")
        if not b64:
            return jsonify({"error": "Missing 'data' field"}), 400

        # Optional limit on number of qubits
        max_qubits = data.get("max_qubits", 10)
        max_len = 2 ** max_qubits

        # Decode base64 -> bytes
        raw_bytes = base64.b64decode(b64)

        # Convert bytes to float array
        raw_ints = np.frombuffer(raw_bytes, dtype=np.uint8)
        raw_floats = raw_ints.astype(np.float64)

        if len(raw_floats) == 0:
            return jsonify({"error": "Empty binary input"}), 400

        # Pad to nearest power-of-two (up to max_qubits)
        L = len(raw_floats)
        pow2_len = 2 ** ceil(log2(L))
        if pow2_len > max_len:
            pow2_len = max_len
        padded = np.zeros(pow2_len, dtype=np.complex128)
        padded[:min(L, pow2_len)] = raw_floats[:min(L, pow2_len)]

        # Normalize to unit vector
        norm = np.linalg.norm(padded)
        if norm == 0:
            return jsonify({"error": "Zero norm not valid quantum state"}), 400
        state = padded / norm

        # Create quantum circuit
        init_gate = Initialize(state.tolist())
        circuit = QuantumCircuit(init_gate.num_qubits)
        circuit.append(init_gate, circuit.qubits)

        # Convert to OpenQASM
        qasm = dumps(circuit)
        qasm_b64 = base64.b64encode(qasm.encode("utf-8")).decode("ascii")

        return jsonify({
            "qasm_base64": qasm_b64,
            "num_qubits": circuit.num_qubits,
            "used_length": pow2_len,
            "norm": norm
        })

    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    app.run(port=5021, debug=True)
