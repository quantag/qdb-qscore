from flask import Flask, request, jsonify
import base64
import logging
import datetime
import json
from flask_cors import CORS

import numpy as np
import sys
from qiskit import QuantumCircuit

# Qiskit:
from qiskit import qasm3 as q3
#from qiskit.circuit.classicalregister import ClassicalRegister
from qiskit.circuit import ClassicalRegister
from qiskit.circuit.library import TwoLocal

#from laboneq._utils import id_generator
#from laboneq.contrib.example_helpers.generate_example_datastore import (
#    generate_example_datastore,
#    get_first_named_entry,
#)
#from laboneq.contrib.example_helpers.plotting.plot_helpers import plot_simulation
#from laboneq.openqasm3.gate_store import GateStore
#from laboneq.pulse_sheet_viewer.pulse_sheet_viewer import show_pulse_sheet
from laboneq.openqasm3.openqasm3_importer import (
    ExternResult,
    exp_from_qasm,
    exp_from_qasm_list,
)


# LabOne Q:
from laboneq.simple import *
from laboneq.simple import DeviceSetup

app = Flask(__name__)
CORS(app)

#logging.basicConfig(filename='app.log', level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Create logger
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Formatter
formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')

# File handler
file_handler = logging.FileHandler('app.log')
file_handler.setFormatter(formatter)
logger.addHandler(file_handler)

# Console handler
console_handler = logging.StreamHandler()
console_handler.setFormatter(formatter)
logger.addHandler(console_handler)


logging.getLogger("laboneq").setLevel(logging.DEBUG)
logging.getLogger("laboneq.simple").setLevel(logging.DEBUG)
logging.getLogger("laboneq.openqasm3").setLevel(logging.DEBUG)


@app.before_request
def log_request_info():
    logging.info("---- Incoming Request ----")
    logging.info("Method: %s URL: %s", request.method, request.url)
    logging.info("Headers: %s", dict(request.headers))
    try:
        logging.info("Body: %s", request.get_data(as_text=True))
    except Exception as e:
        logging.warning("Could not log body: %s", str(e))
    logging.info("--------------------------")

def load_program_from_file(filename):
    try:
        with open(filename, 'r') as file:
            program = file.read()
        return program
    except FileNotFoundError:
        print(f"Error: File '{filename}' not found.")
        return None
def execCode(src):
    logging.info(f"Received code: {src}")

    # Fake qubit map for testing
    q0, q1 = "q0", "q1"
    qubit_map = {"_qubit0": q0, "_qubit1": q1}

    # Just return the input for now
    result = {"received_qasm": src, "mapped_qubits": qubit_map}
    return result


@app.route('/run', methods=['POST'])
def runCode():
    logging.info("New request")

    try:
        data = request.json

        qasm_src = base64.b64decode(data['qasm']).decode()
        yaml_src = base64.b64decode(data['setup']).decode()

        logging.info("Incoming QASM: %s", qasm_src)
        logging.info("Incoming YAML: %s", yaml_src)

        # Save files (optional, for debugging)
        timestamp = datetime.datetime.now().strftime("%Y%m%d%H%M%S%f")
        qasm_file = f"scripts/script{timestamp}.qasm"
        yaml_file = f"scripts/setup{timestamp}.yaml"
        with open(qasm_file, "w") as f: f.write(qasm_src)
        with open(yaml_file, "w") as f: f.write(yaml_src)

        # Load device setup
        device_setup = DeviceSetup.from_yaml(yaml_file)

        [q0, q1] = device_setup.qubits[:2]
        qubit_map = {"_qubit0": q0, "_qubit1": q1}

        exp = exp_from_qasm(qasm_src, qubits=qubit_map)
        session = Session(device_setup=device_setup)
        session.connect(do_emulation=True)
        compiled = session.compile(exp)
        results = session.run(compiled)

        encoded_result = base64.b64encode(str(results.acquired_results).encode()).decode()
        return jsonify({"status": 0, "res": encoded_result})

    except Exception as e:
        logging.error("Error: %s", str(e))
        return jsonify({"status": 2, "err": str(e)})

if __name__ == '__main__':
    app.run(debug=True, port=5801)
