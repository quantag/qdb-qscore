from flask import Flask, request, jsonify
import cudaq
import math
import sys

app = Flask(__name__)

def parse_angle(expr: str) -> float:
    expr = expr.strip().replace(";", "")
    if expr == "pi":
        return math.pi
    if expr.startswith("pi/"):
        denom = float(expr.split("/")[1])
        return math.pi / denom
    if "*" in expr and "pi" in expr:
        # e.g. "3*pi/8"
        parts = expr.split("*")
        factor = float(parts[0])
        rest = parts[1]
        if "/" in rest:
            denom = float(rest.split("/")[1])
            return factor * math.pi / denom
        return factor * math.pi
    if "/" in expr and "pi" in expr:
        # e.g. "pi/2" (already covered above, but just in case)
        num, denom = expr.split("/")
        num = num.replace("pi", str(math.pi))
        return float(num) / float(denom)
    try:
        return float(expr)
    except Exception:
        raise ValueError(f"Unsupported angle format: {expr}")


def qasm_to_kernel(qasm: str):
    """Translate a subset of OpenQASM 2.0 into a CUDA-Q kernel."""
    kernel = cudaq.make_kernel()
    q = None
    creg_size = 0

    for line in qasm.splitlines():
        line = line.strip()
        if (not line
            or line.startswith("//")
            or line.startswith("OPENQASM")
            or line.startswith("include")):
            continue
        print(f"[DEBUG] parsing line: {line}", file=sys.stderr)
        if line.startswith("qreg"):
            n = int(line.split("[")[1].split("]")[0])
            q = kernel.qalloc(n)
            print(f"[DEBUG] allocated qreg with {n} qubits", file=sys.stderr)

        elif line.startswith("creg"):
            creg_size = int(line.split("[")[1].split("]")[0])

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
            kernel.rz(parse_angle(angle), q[idx])

        elif line.startswith("cu1"):
            line = line.replace(";", "")
            angle = line[line.find("(")+1:line.find(")")]
            ctrl_idx = int(line.split("[")[1].split("]")[0])
            tgt_idx  = int(line.split("[")[2].split("]")[0])

            theta = parse_angle(angle)
            try:
                kernel.cp(theta, q[ctrl_idx], q[tgt_idx])
            except Exception:
                kernel.cr1(theta, q[ctrl_idx], q[tgt_idx])


        elif line.startswith("barrier"):
            continue  # ignore

        elif line.startswith("measure"):
            continue  # handled by cudaq.sample

    return kernel, creg_size

@app.route("/run", methods=["POST"])
def run_qasm():
    qasm = request.json.get("qasm")
    shots = request.json.get("shots", 1000)

    if not qasm:
        return jsonify({"error": "no qasm provided"}), 400

    try:
        kernel, creg_size = qasm_to_kernel(qasm)
        result = cudaq.sample(kernel, shots_count=shots)

        # Build histogram with optional padding to creg size
        histogram = {}
        for bitstring, count in result.items():
            if not isinstance(bitstring, str):
                bitstring = "".join(str(b) for b in bitstring)
            if creg_size and len(bitstring) < creg_size:
                bitstring = bitstring.zfill(creg_size)
            histogram[bitstring] = count

        return jsonify({"result": histogram})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5005)
