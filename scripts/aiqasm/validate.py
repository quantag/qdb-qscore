from qiskit.qasm2 import loads as load_qasm2, QASM2ParseError
from qiskit.qasm3 import loads as load_qasm3

def detect_version(qasm_code: str) -> str:
    if qasm_code.strip().startswith("OPENQASM 3"):
        return "3.0"
    elif qasm_code.strip().startswith("OPENQASM 2"):
        return "2.0"
    return "unknown"

def validate_qasm(qasm_code: str) -> dict:
    version = detect_version(qasm_code)

    try:
        if version == "2.0":
            load_qasm2(qasm_code)
        elif version == "3.0":
            load_qasm3(qasm_code)
        else:
            return {"valid": False, "version": "unknown", "error": "Cannot detect OpenQASM version."}
    except QASM2ParseError as e:
        return {"valid": False, "version": version, "error": str(e)}
    except Exception as e:
        return {"valid": False, "version": version, "error": f"{type(e).__name__}: {str(e)}"}

    return {"valid": True, "version": version}
