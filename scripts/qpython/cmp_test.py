
import time
import sys
from qiskit import qasm2
from qiskit_aer import AerSimulator
from quantag.vm import QuantagVM


def testQuantagVM(qc, shots):
    backend = QuantagVM(
        api_key="27891cd9184882059389796eee875b46c3fd8bf1bd42af1e9c14e8961c35ba7d",
        backend_type="cudaq"
    )
    job = backend.run(qc, shots=shots)
    result = job.result()
    return result


def testAer(qc, shots):
    backend = AerSimulator()
    job = backend.run(qc, shots=shots)
    result = job.result()
    return result


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python cmp_test.py <file.qasm> [shots]")
        sys.exit(1)

    qasm_file = sys.argv[1]
    shots = int(sys.argv[2]) if len(sys.argv) > 2 else 100

    qc = qasm2.load(qasm_file)

    # QuantagVM test
    print("=== QuantagVM ===")
    start = time.perf_counter()
    result_qvm = testQuantagVM(qc, shots)
    end = time.perf_counter()
    print("Counts:", result_qvm.get_counts())
    print(f"Execution time: {end - start:.3f} seconds\n")

    # Qiskit Aer test
    print("=== Qiskit Aer ===")
    start = time.perf_counter()
    result_aer = testAer(qc, shots)
    end = time.perf_counter()
    print("Counts:", result_aer.get_counts())
    print(f"Execution time: {end - start:.3f} seconds")
