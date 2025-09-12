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

logging.basicConfig(filename='app.log', level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def load_program_from_file(filename):
    try:
        with open(filename, 'r') as file:
            program = file.read()
        return program
    except FileNotFoundError:
        print(f"Error: File '{filename}' not found.")
        return None

def execCode(src):
    setup_db = generate_example_datastore(path="", filename=":memory:")
    device_setup = get_first_named_entry(
        db=setup_db,
        name="12_tuneable_qubit_setup_shfsg_shfqa_shfqc_hdawg_pqsc_calibrated",
    )
    [q0, q1] = device_setup.qubits[:2]
    qubit_map = {"_qubit0": q0, "_qubit1": q1}
    gate_store = GateStore()

    #print("Received OpenQASM:\n" + src)
    logging.info(f"Received code: {src}")
    exp = exp_from_qasm(src, qubits=qubit_map, gate_store=gate_store)
    logging.info(f"After exp_from_qasm ~~~~~")
    my_session = Session(device_setup=device_setup)
    my_session.connect(do_emulation=True)
    compiled_exp = my_session.compile(exp)
    my_results = my_session.run(compiled_exp)
    return my_results.acquired_results

@app.route('/run', methods=['POST'])
def runCode():
    logging.info(f"New request");
    logging.info(f"Incoming request: {request.json}")
    try:
        data = request.json
        decodedSrc = base64.b64decode(data['src'])
        logging.info(f"Incoming script: {decodedSrc.decode()}")

        timestamp = datetime.datetime.now().strftime("%Y%m%d%H%M%S%f")
        script_filename = f"scripts/script{timestamp}.qasm"
        with open(script_filename, 'w') as f:
            f.write(decodedSrc.decode())

        result = execCode(decodedSrc.decode())
        
        encoded_result = base64.b64encode(str(result).encode()).decode()
        logging.info(f"Execution result: {result}")
        return jsonify({'status':0,'res': encoded_result})
    except Exception as e:
        logging.error(f"An error occurred: {str(e)}")
        return jsonify({'status':2,'err': str(e)})

if __name__ == '__main__':
    app.run(debug=True, port=5801)
