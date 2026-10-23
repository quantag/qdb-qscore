/*
 * Copyright (c) 2024 Quantag IT Solutions GmbH
 *
 * This source code is licensed under the MIT license found in the
 * LICENSE file in the root directory of this source tree.
 */

// Python code that CudaQProcessor adds around a CUDA-Q program before it is sent to
// the Python executor (qdb-decom). The program runs unchanged; its output is kept
// out of the result, and at the end the kernel to debug is converted to OpenQASM 2.0:
//  1. cudaq.translate(kernel, format="openqasm2") for kernels that call no other kernels;
//  2. otherwise cudaq.translate(kernel, format="qir-adaptive") (all calls inlined) and
//     the QIR gate calls are converted to OpenQASM 2.0 (qelib1.inc gates only).
// The kernel is the one passed to cudaq.sample/observe/... (hint) or the last kernel
// without parameters. Verified with cudaq 0.16.0 (state vectors compared with Qiskit).

#pragma once

// Inserted before the program (after "from __future__" imports)
static const char* const CUDAQ_PROLOGUE = R"QSPY(# --- Quantag QSCore: keep prints of the user code out of the result (prepended by CudaQProcessor) ---
import sys as _qs_sys, io as _qs_io
_qs_saved_stdout = _qs_sys.stdout
_qs_sys.stdout = _qs_io.StringIO()
)QSPY";

// Appended after the program and the line "_QS_KERNEL_HINT = <name or None>"
static const char* const CUDAQ_EPILOGUE = R"QSPY(# --- Quantag QSCore: CUDA-Q kernel -> OpenQASM 2.0 (appended by CudaQProcessor) ---
def _qs_cudaq_to_qasm(_qs_ns, _qs_hint):
    import math
    import re
    import struct
    import cudaq

    def is_kernel(obj):
        try:
            from cudaq.kernel.kernel_decorator import isa_kernel_decorator
            return isa_kernel_decorator(obj)
        except Exception:
            return hasattr(obj, "formal_arity") and hasattr(obj, "launch_args_required")

    kernels = {n: o for n, o in list(_qs_ns.items()) if not n.startswith("_qs_") and is_kernel(o)}
    if not kernels:
        raise RuntimeError("QSCore: no @cudaq.kernel found in the file")
    if _qs_hint and _qs_hint in kernels:
        name = _qs_hint
    else:
        free = [n for n, k in kernels.items() if k.formal_arity() == 0]
        if not free:
            raise RuntimeError("QSCore: debugging needs a CUDA-Q kernel without parameters "
                               "(found only kernels with parameters: " + ", ".join(kernels) + ")")
        name = free[-1]
    kernel = kernels[name]
    if kernel.formal_arity() != 0:
        raise RuntimeError("QSCore: kernel '" + name + "' has parameters; debugging needs a kernel without parameters")

    # 1. Direct translation (works for kernels that do not call other kernels)
    try:
        return cudaq.translate(kernel, format="openqasm2")
    except Exception:
        pass

    # 2. Kernels that call other kernels: translate to QIR (adaptive profile, all
    #    calls inlined, static qubits) and convert the gate calls to OpenQASM 2.0.
    qir = cudaq.translate(kernel, format="qir-adaptive")

    def operands(text):
        out, depth, cur = [], 0, ""
        for ch in text:
            if ch == "(":
                depth += 1
            elif ch == ")":
                depth -= 1
            if ch == "," and depth == 0:
                out.append(cur.strip())
                cur = ""
            else:
                cur += ch
        if cur.strip():
            out.append(cur.strip())
        return out

    def qubit(op):
        if re.search(r"\bnull\b", op):
            return 0
        m = re.search(r"inttoptr\s*\(\s*i64\s+(\d+)\s+to", op)
        if not m:
            raise RuntimeError("QSCore: dynamic qubit addressing is not supported: " + op)
        return int(m.group(1))

    def number(op):
        v = op.split()[-1]
        if v.lower().startswith("0x"):
            return struct.unpack(">d", bytes.fromhex(v[2:].rjust(16, "0")))[0]
        return float(v)

    def ang(x):
        return repr(float(x))

    simple = {"h": "h", "x": "x", "y": "y", "z": "z", "s": "s", "t": "t"}
    adjoint = {"s": "sdg", "t": "tdg"}
    rotation = {"rx": "rx", "ry": "ry", "rz": "rz", "r1": "u1"}
    lines, nq, ncl = [], 0, 0

    def q(i):
        nonlocal nq
        nq = max(nq, i + 1)
        return "q[%d]" % i

    def controlled(op, params, ctrls, targets):
        c, t = [q(i) for i in ctrls], [q(i) for i in targets]
        k = len(c)
        if op == "x" and k == 1:
            return ["cx %s, %s;" % (c[0], t[0])]
        if op == "x" and k == 2:
            return ["ccx %s, %s, %s;" % (c[0], c[1], t[0])]
        if op == "z" and k == 1:
            return ["cz %s, %s;" % (c[0], t[0])]
        if op == "z" and k == 2:
            return ["h %s;" % t[0], "ccx %s, %s, %s;" % (c[0], c[1], t[0]), "h %s;" % t[0]]
        if k != 1:
            raise RuntimeError("QSCore: %s with %d controls is not supported" % (op, k))
        if op == "y":
            return ["cy %s, %s;" % (c[0], t[0])]
        if op == "h":
            return ["ch %s, %s;" % (c[0], t[0])]
        if op in ("s", "t", "sdg", "tdg"):
            a = {"s": math.pi / 2, "t": math.pi / 4, "sdg": -math.pi / 2, "tdg": -math.pi / 4}[op]
            return ["cu1(%s) %s, %s;" % (ang(a), c[0], t[0])]
        if op == "rz":
            return ["crz(%s) %s, %s;" % (ang(params[0]), c[0], t[0])]
        if op == "r1":
            return ["cu1(%s) %s, %s;" % (ang(params[0]), c[0], t[0])]
        if op == "rx":
            return ["cu3(%s,%s,%s) %s, %s;" % (ang(params[0]), ang(-math.pi / 2), ang(math.pi / 2), c[0], t[0])]
        if op == "ry":
            return ["cu3(%s,0,0) %s, %s;" % (ang(params[0]), c[0], t[0])]
        if op == "swap":  # controlled swap via Toffoli (cswap is not in qelib1.inc)
            return ["cx %s, %s;" % (t[1], t[0]), "ccx %s, %s, %s;" % (c[0], t[0], t[1]), "cx %s, %s;" % (t[1], t[0])]
        raise RuntimeError("QSCore: controlled %s is not supported" % op)

    call_re = re.compile(r"call\s+[^@]*@([\w.]+)\s*\((.*)\)\s*$")
    for raw in qir.splitlines():
        m = call_re.search(raw.strip())
        if not m:
            continue
        fn, args = m.group(1), operands(m.group(2))
        if fn == "generalizedInvokeWithRotationsControlsTargets":
            nrot, narr, nctl, ntgt = (int(a.split()[-1]) for a in args[:4])
            fm = re.search(r"@__quantum__qis__(\w+?)__(ctl|ctladj)\b", args[4])
            if not fm or narr:
                raise RuntimeError("QSCore: unsupported controlled call: " + raw.strip())
            op = fm.group(1)
            if fm.group(2) == "ctladj":
                op = {"s": "sdg", "t": "tdg"}.get(op, op)
            rest = args[5:]
            params = [number(a) for a in rest[:nrot]]
            if fm.group(2) == "ctladj" and op in rotation:
                params = [-p for p in params]
            ctrls = [qubit(a) for a in rest[nrot:nrot + nctl]]
            targets = [qubit(a) for a in rest[nrot + nctl:nrot + nctl + ntgt]]
            lines += controlled(op, params, ctrls, targets)
            continue
        qm = re.match(r"__quantum__qis__(\w+?)__(body|adj)$", fn)
        if not qm:
            continue  # runtime calls (allocation, output recording, ...)
        op, kind = qm.groups()
        if op in ("mz", "m"):
            i, r = qubit(args[0]), qubit(args[1]) if len(args) > 1 else 0
            ncl = max(ncl, r + 1)
            lines.append("measure %s -> c[%d];" % (q(i), r))
        elif op == "reset":
            lines.append("reset %s;" % q(qubit(args[0])))
        elif op in simple and kind == "body":
            lines.append("%s %s;" % (simple[op], q(qubit(args[0]))))
        elif op in adjoint and kind == "adj":
            lines.append("%s %s;" % (adjoint[op], q(qubit(args[0]))))
        elif op in ("x", "y", "z", "h") and kind == "adj":
            lines.append("%s %s;" % (op, q(qubit(args[0]))))
        elif op in rotation:
            a = number(args[0]) * (-1 if kind == "adj" else 1)
            lines.append("%s(%s) %s;" % (rotation[op], ang(a), q(qubit(args[1]))))
        elif op == "u3":
            a = [number(x) for x in args[:3]]
            lines.append("u3(%s,%s,%s) %s;" % (ang(a[0]), ang(a[1]), ang(a[2]), q(qubit(args[3]))))
        elif op == "cnot":
            lines.append("cx %s, %s;" % (q(qubit(args[0])), q(qubit(args[1]))))
        elif op == "cz":
            lines.append("cz %s, %s;" % (q(qubit(args[0])), q(qubit(args[1]))))
        elif op == "swap":  # swap is not in qelib1.inc
            a, b = q(qubit(args[0])), q(qubit(args[1]))
            lines += ["cx %s, %s;" % (a, b), "cx %s, %s;" % (b, a), "cx %s, %s;" % (a, b)]
        else:
            raise RuntimeError("QSCore: CUDA-Q operation '%s' is not supported" % op)

    m = re.search(r'"(?:requiredQubits|required_num_qubits)"="(\d+)"', qir)
    if m:
        nq = max(nq, int(m.group(1)))
    m = re.search(r'"(?:requiredResults|required_num_results)"="(\d+)"', qir)
    if m and ncl:
        ncl = max(ncl, int(m.group(1)))
    head = ["// Converted from CUDA-Q kernel '%s' by QSCore" % name, "OPENQASM 2.0;", 'include "qelib1.inc";',
            "qreg q[%d];" % max(nq, 1)]
    if ncl:
        head.append("creg c[%d];" % ncl)
    return "\n".join(head + lines) + "\n"


code777 = _qs_cudaq_to_qasm(globals(), _QS_KERNEL_HINT)
)QSPY";

// Appended last: restores stdout so the executor can print the result
static const char* const CUDAQ_RESTORE_STDOUT = R"QSPY(_qs_sys.stdout = _qs_saved_stdout
)QSPY";
