from qiskit import QuantumCircuit
from quantag.vm import QuantagVM

API_KEY = "27891cd9184882059389796eee875b46c3fd8bf1bd42af1e9c14e8961c35ba7d"
SERVER_URL = "https://quantum.quantag-it.com/api5"

# Build a simple Bell circuit
qc = QuantumCircuit(2)
qc.h(0)
qc.cx(0, 1)
qc.measure_all()

print("=== SYNC WORKFLOW ===")
backend_sync = QuantagVM(api_key=API_KEY, server_url=SERVER_URL, backend_type="cudaq", async_mode=False)
job_sync = backend_sync.run(qc, shots=100)
result_sync = job_sync.result()
print("Sync result:", result_sync.get_counts())

print("\n=== ASYNC WORKFLOW ===")
backend_async = QuantagVM(api_key=API_KEY, server_url=SERVER_URL, backend_type="cudaq", async_mode=True)
job_async = backend_async.run(qc, shots=100)
print("Submitted async job with ID:", job_async.job_id())
print("Initial status:", job_async.status())

# Wait until done and fetch results
result_async = job_async.result()
print("Async result:", result_async.get_counts())
