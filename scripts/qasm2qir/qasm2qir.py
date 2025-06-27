from flask import Flask, request, jsonify
from qiskit import QuantumCircuit, transpile
from qiskit_aer import AerSimulator
from qiskit.visualization import plot_histogram
from qiskit import qasm3
from qiskit import qasm2
import io
import urllib, base64
from qbraid_qir.qasm3 import qasm3_to_qir

app = Flask(__name__)


@app.route('/qasm2qir', methods=['POST'])
def create_resource():
    data = request.get_json()
    if not data or 'qasm' not in data:
        return jsonify({"status": "1", "error": "Missing 'qasm' in JSON"}), 400
 
    try:
        # Decode Base64 input
        qasm_base64 = data['qasm']
        qasm_bytes = base64.b64decode(qasm_base64)
        qasm3_code = qasm_bytes.decode('utf-8')
        print("Received QASM:\n", qasm3_code)
 
        # Convert QASM to QIR
        qir_output = qasm3_to_qir(qasm3_code)

        # Encode output to Base64
        qir_bytes = str(qir_output).encode('utf-8')
        qir_base64 = base64.b64encode(qir_bytes).decode('utf-8')
 
        return jsonify({"status": "0", "qir": qir_base64}), 200
 
    except Exception as e:
        return jsonify({"status": "2", "error": str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True, port=5007)  
