def generate_medium_qasm(file_path, num_qubits=6, num_layers=200):
    with open(file_path, "w") as f:
        f.write("OPENQASM 2.0;\n")
        f.write('include "qelib1.inc";\n')
        f.write(f"qreg q[{num_qubits}];\n")
        f.write(f"creg c[{num_qubits}];\n\n")
        
        for layer in range(num_layers):
            f.write(f"// Layer {layer + 1}\n")
            for i in range(num_qubits):
                f.write(f"h q[{i}];\n")
            for i in range(num_qubits - 1):
                f.write(f"cx q[{i}], q[{i+1}];\n")
            for i in range(num_qubits):
                f.write(f"measure q[{i}] -> c[{i}];\n")
            f.write("\n")

    print(f"Generated {file_path} with {num_qubits} qubits and {num_layers} layers.")

generate_medium_qasm("medium_test.qasm", num_qubits=6, num_layers=200)
