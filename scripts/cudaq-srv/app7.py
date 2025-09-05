from flask import Flask, request, jsonify
import cudaq

app = Flask(__name__)

def qasm_to_kernel(qasm: str):
    kernel = cudaq.make_kernel()
    q = None

    for line in qasm.splitlines():
        line = line.strip()
        if (not line
            or line.startswith("//")
            or line.startswith("OPENQASM")
            or line.startswith("include")
            or line.startswith("creg")):
            continue

        if line.startswith("qreg"):
            n = int(line.split("[")[1].split("]")[0])
            q = kernel.qalloc(n)

        elif line.startswith("h "):
            idx = int(line.split("[")[1].split("]")[0])
            kernel.h(q[idx])

        elif line.startswith("x "):
            idx = int(line.split("[")[1].split("]")[0])
            kernel.x(q[idx])

        elif line.startswith("cx"):
            parts = line.replace(";", "").split(",")
            c1 = int(parts[0].split("[")[1].split("]")[0])
            c2 = int(parts[1].split("[")[1].split("]")[0])
            kernel.cx(q[c1], q[c2])

        elif line.startswith("rz"):
            angle = line[line.find("(")+1:line.find(")")]
            idx = int(line.split("[")[1].split("]")[0])
            kernel.rz(float(angle), q[idx])

        elif line.startswith("measure"):
            # handled by cudaq.sample
            continue

    return kernel


@app.route("/run", methods=["POST"])
def run_qasm():
    qasm = request.json.get("qasm")
    shots = request.json.get("shots", 1000)

    if not qasm:
        return jsonify({"error": "no qasm provided"}), 400

    try:
        kernel = qasm_to_kernel(qasm)
        result = cudaq.sample(kernel, shots_count=shots)

        # Build histogram properly
        histogram = {}
        for bitstring, count in result.items():
            if not isinstance(bitstring, str):
                bitstring = "".join(str(b) for b in bitstring)
            histogram[bitstring] = count

        return jsonify({"result": histogram})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5005)
