def generate_big_qasm(file_path, num_qubits=10, num_layers=1000):
    with open(file_path, "w") as f:
        f.write("OPENQASM 2.0;\n")
        f.write('include "qelib1.inc";\n')
        f.write(f"qreg q[{num_qubits}];\n")
        for _ in range(num_layers):
            for i in range(num_qubits):
                f.write(f"h q[{i}];\n")
            for i in range(0, num_qubits - 1):
                f.write(f"cx q[{i}], q[{i+1}];\n")

generate_big_qasm("big_test.qasm", num_qubits=8, num_layers=500)
