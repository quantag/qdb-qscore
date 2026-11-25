"""Tests of the Qiskit debug bridge (processors/QiskitBridge.h).

The bridge runs a Qiskit program and reports the program line of every QASM
instruction. Run with a Python that has qiskit (tested with qiskit 2.5.2):

    python3 test/python/test_qiskit_bridge.py
"""
import base64
import re
import subprocess
import sys
import textwrap
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
HEADER = ROOT / "processors" / "QiskitBridge.h"
MARKER = "// qscore-lines:"


def bridge_source():
    text = HEADER.read_text(encoding="utf-8")
    match = re.search(r'R"QSPY\((.*)\)QSPY"', text, re.S)
    assert match, "QISKIT_BRIDGE not found in QiskitBridge.h"
    return match.group(1)


def run(program, image="", root=None, program_path=None, cwd=None):
    """Runs the bridge like qdb-decom in env mode; returns (exit code, result, stderr)."""
    b64 = base64.b64encode(program.encode("utf-8")).decode()
    script = bridge_source() + "\ncode777 = _qs_qiskit_debug(%r, %r, %r, %r)\n" % (b64, image, root, program_path)
    script += ("\n\nimport sys\nresult = globals().get('code777', None)\n"
               "sys.stdout.write('' if result is None else str(result))\n")
    proc = subprocess.run([sys.executable, "-c", script], capture_output=True, text=True, timeout=300, cwd=cwd)
    return proc.returncode, proc.stdout, proc.stderr


def instruction_lines(result):
    """[(QASM instruction, program line)] from a bridge result."""
    lines = result.splitlines()
    assert lines and lines[-1].startswith(MARKER), "no source lines in the result:\n" + result
    numbers = [int(n) for n in lines[-1][len(MARKER):].split(",")]
    qasm = lines[:-1]
    assert len(numbers) == len(qasm)
    declaration = re.compile(r"^\s*((OPENQASM|include|qreg|creg|gate|opaque|barrier)\b|//|$)")
    return [(q.strip(), n) for q, n in zip(qasm, numbers) if not declaration.match(q)]


def program_line(program, text):
    """1-based line of the program that contains text (exactly once)."""
    found = [i + 1 for i, line in enumerate(program.splitlines()) if text in line]
    assert len(found) == 1, (text, found)
    return found[0]


PASSED, FAILED = [], []


def case(name):
    def wrap(fn):
        try:
            fn()
            PASSED.append(name)
            print("OK  ", name)
        except Exception as error:  # noqa: BLE001
            FAILED.append(name)
            print("FAIL", name, "-", error)
        return fn
    return wrap


@case("straight-line program, broadcast gates, comments and prints do not shift lines")
def _():
    program = textwrap.dedent('''\
        """Module docstring."""
        from qiskit import QuantumCircuit
        print("start")

        # comment
        qc = QuantumCircuit(2, 2)
        qc.h([0, 1])  # broadcast: two instructions
        print("between")
        qc.cz(0, 1)
        qc.measure([0, 1], [0, 1])
        ''')
    code, out, err = run(program)
    assert code == 0, err
    got = instruction_lines(out)
    h, cz, m = (program_line(program, t) for t in ("qc.h(", "qc.cz(", "qc.measure("))
    assert [n for _, n in got] == [h, h, cz, m, m], got
    assert "start" not in out and "between" not in out


@case("loops and functions: instructions get the line inside the function")
def _():
    program = textwrap.dedent('''\
        import math
        from qiskit import QuantumCircuit


        def layer(qc, n, theta):
            for q in range(n):
                qc.ry(theta, q)
            for q in range(n - 1):
                qc.cx(q, q + 1)


        def build():
            qc = QuantumCircuit(3, 3)
            qc.h(0)
            for step in range(2):
                layer(qc, 3, math.pi / (step + 2))
                qc.z(2)
            qc.barrier()
            qc.measure(range(3), range(3))
            return qc


        if __name__ == "__main__":
            circuit = build()
        ''')
    code, out, err = run(program)
    assert code == 0, err
    got = [n for _, n in instruction_lines(out)]
    h, ry, cx, z, m = (program_line(program, t) for t in ("qc.h(", "qc.ry(", "qc.cx(", "qc.z(", "qc.measure("))
    assert got == [h] + ([ry] * 3 + [cx] * 2 + [z]) * 2 + [m] * 3, got


@case("custom gates (append, compose) and the circuit chosen by its variable")
def _():
    program = textwrap.dedent('''\
        from qiskit import QuantumCircuit

        w = QuantumCircuit(2, name="W")
        w.h(0)
        w.cx(0, 1)
        w_gate = w.to_gate()

        sub = QuantumCircuit(2)
        sub.x(1)

        circuit = QuantumCircuit(2, 2)
        circuit.append(w_gate, [0, 1])
        circuit.compose(sub, inplace=True)
        circuit.measure([0, 1], [0, 1])
        ''')
    code, out, err = run(program)
    assert code == 0, err
    got = instruction_lines(out)
    assert got[0][0].split()[0] in ("W", "gate_W"), got
    a, c, m = (program_line(program, t) for t in ("circuit.append(", "circuit.compose(", "circuit.measure("))
    assert [n for _, n in got] == [a, c, m, m], got


@case("circuit image is written")
def _():
    import tempfile
    image = Path(tempfile.mkdtemp()) / "session.png"
    code, out, err = run("from qiskit import QuantumCircuit\nqc = QuantumCircuit(1)\nqc.h(0)\n", str(image))
    assert code == 0, err
    if "circuit image not drawn" in err:
        print("     (matplotlib not installed, image skipped)")
    else:
        assert image.exists() and image.stat().st_size > 0


@case("program without a circuit fails with a clear message")
def _():
    code, out, err = run("x = 1\nprint(x)\n")
    assert code != 0 and "no QuantumCircuit found" in err, err


@case("program errors keep the program's line numbers")
def _():
    code, out, err = run("from qiskit import QuantumCircuit\n\nqc = QuantumCircuit(1)\nraise ValueError('boom')\n")
    assert code != 0 and 'File "<qscore-program>", line 4' in err, err
    code, out, err = run("from qiskit import QuantumCircuit\n\nqc = QuantumCircuit(1)\nraise ValueError('boom')\n",
                         program_path="/project/main.py")
    assert code != 0 and 'File "/project/main.py", line 4' in err, err


@case("project root: local package import, relative data path, __file__")
def _():
    import tempfile
    root = Path(tempfile.mkdtemp())
    (root / "lib").mkdir()
    (root / "lib" / "__init__.py").write_text("")
    (root / "lib" / "gates.py").write_text("def entangle(qc):\n    qc.cx(0, 1)\n")
    (root / "quantum").mkdir()
    (root / "quantum" / "helper.py").write_text("ANGLE = 0.5\n")
    (root / "data").mkdir()
    (root / "data" / "n.txt").write_text("2\n")
    program = textwrap.dedent('''\
        import os
        from qiskit import QuantumCircuit
        from lib.gates import entangle
        from helper import ANGLE
        n = int(open("data/n.txt").read())
        here = os.path.dirname(__file__)
        qc = QuantumCircuit(n)
        qc.ry(ANGLE, 0)
        entangle(qc)
        assert os.path.basename(here) == "quantum"
        ''')
    (root / "quantum" / "main.py").write_text(program)
    elsewhere = tempfile.mkdtemp()
    code, out, err = run(program, root=str(root), program_path=str(root / "quantum" / "main.py"), cwd=elsewhere)
    assert code == 0, err
    got = instruction_lines(out)
    assert [g.split()[0].split("(")[0] for g, _ in got] == ["ry", "cx"], got
    # the cx comes from lib/gates.py: its line is not a line of main.py, so it gets the call line
    assert [n for _, n in got] == [program_line(program, "qc.ry("), program_line(program, "entangle(qc)")], got


@case("in one process (executor without a venv): local modules, cwd and sys.path do not leak to the next program")
def _():
    import tempfile
    script = bridge_source() + textwrap.dedent('''
        import base64, os, sys, tempfile
        from pathlib import Path
        def project(value):
            root = Path(tempfile.mkdtemp())
            (root / "helper.py").write_text("N = %d\\n" % value)
            prog = "from qiskit import QuantumCircuit\\nfrom helper import N\\nqc = QuantumCircuit(N)\\nqc.h(0)\\n"
            (root / "main.py").write_text(prog)
            return str(root), str(root / "main.py"), base64.b64encode(prog.encode()).decode()
        cwd, path = os.getcwd(), list(sys.path)
        out = []
        for value in (1, 3):
            root, main, b64 = project(value)
            qasm = _qs_qiskit_debug(b64, "", root, main)
            out.append([l for l in qasm.splitlines() if l.startswith("qreg")][0])
        assert os.getcwd() == cwd and sys.path == path and "helper" not in sys.modules
        print(out)
        ''')
    proc = subprocess.run([sys.executable, "-c", script], capture_output=True, text=True, timeout=300)
    assert proc.returncode == 0, proc.stderr[-800:]
    assert "['qreg q[1];', 'qreg q[3];']" in proc.stdout, proc.stdout


@case("without a project root the program still runs (old QSCore call)")
def _():
    code, out, err = run("from qiskit import QuantumCircuit\nqc = QuantumCircuit(1)\nqc.h(0)\n")
    assert code == 0, err


@case("many temporary circuits next to a long-lived one: tracing stays linear")
def _():
    # An optimizer loop builds a new circuit per evaluation while a module-level circuit
    # stays alive. Freed circuits must not stay in the tracking list (sync runs on every
    # program line), or the run time grows quadratically.
    program = textwrap.dedent('''\
        from qiskit import QuantumCircuit
        step = QuantumCircuit(1)
        step.x(0)
        def build(angle):
            circuit = QuantumCircuit(1)
            circuit.rx(angle, 0)
            return circuit
        total = 0
        for i in range(30000):
            total += len(build(i * 0.001).data)
        qc = QuantumCircuit(1, 1)
        qc.h(0)
        qc.measure(0, 0)
        ''')
    import time
    start = time.time()
    code, out, err = run(program)
    elapsed = time.time() - start
    assert code == 0, err
    got = [n for _, n in instruction_lines(out)]
    assert got == [program_line(program, "qc.h(0)"), program_line(program, "qc.measure(0, 0)")], got
    assert elapsed < 30, "%.0f s, expected a few seconds" % elapsed


print("%d passed, %d failed" % (len(PASSED), len(FAILED)))
sys.exit(1 if FAILED else 0)
