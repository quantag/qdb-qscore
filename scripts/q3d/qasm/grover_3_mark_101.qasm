OPENQASM 2.0;
include "qelib1.inc";

qreg q[3];
creg c[3];

// superposition
h q[0]; h q[1]; h q[2];

// ---- ORACLE: mark |101>
// Flip zeros in target pattern (bit 1 is 0)
x q[1];
// CCZ via H-CCX-H on the last qubit
h q[2];
ccx q[0], q[1], q[2];
h q[2];
// unflip
x q[1];

// ---- DIFFUSION (inversion about mean)
h q[0]; h q[1]; h q[2];
x q[0]; x q[1]; x q[2];
h q[2];
ccx q[0], q[1], q[2];
h q[2];
x q[0]; x q[1]; x q[2];
h q[0]; h q[1]; h q[2];

barrier q;
measure q -> c;
