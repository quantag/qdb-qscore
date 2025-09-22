import time
from qiskit import QuantumCircuit
from qiskit_aer import Aer
from quantag.vm import QuantagVM


def testQuantagVM():
    qc = QuantumCircuit(2)
    qc.h(0)
    qc.cx(0, 1)
    qc.measure_all()

    backend = QuantagVM(
        api_key="27891cd9184882059389796eee875b46c3fd8bf1bd42af1e9c14e8961c35ba7d",
        backend_type="cudaq"
    )

    job = backend.run(qc, shots=100)
    result = job.result()
    return result


def testAer():
    qc = QuantumCircuit(2)
    qc.h(0)
    qc.cx(0, 1)
    qc.measure_all()

    backend = Aer.get_backend("aer_simulator")
    job = backend.run(qc, shots=100)
    result = job.result()
    return result


if __name__ == "__main__":
    print("=== QuantagVM ===")
    start = time.perf_counter()
    result_vm = testQuantagVM()
    end = time.perf_counter()
    print("Counts:", result_vm.get_counts())
    print(f"Execution time: {end - start:.3f} seconds\n")

    print("=== Qiskit Aer ===")
    start = time.perf_counter()
    result_aer = testAer()
    end = time.perf_counter()
    print("Counts:", result_aer.get_counts())
    print(f"Execution time: {end - start:.3f} seconds")
