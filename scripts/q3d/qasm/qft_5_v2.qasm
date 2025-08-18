OPENQASM 2.0;
include "qelib1.inc";

qreg q[5];

// QFT on 5 qubits (q[0] is LSB)

// stage for q[0]
cu1(pi/2)  q[1], q[0];
cu1(pi/4)  q[2], q[0];
cu1(pi/8)  q[3], q[0];
cu1(pi/16) q[4], q[0];
h q[0];

// stage for q[1]
cu1(pi/2)  q[2], q[1];
cu1(pi/4)  q[3], q[1];
cu1(pi/8)  q[4], q[1];
h q[1];

// stage for q[2]
cu1(pi/2)  q[3], q[2];
cu1(pi/4)  q[4], q[2];
h q[2];

// stage for q[3]
cu1(pi/2)  q[4], q[3];
h q[3];

// stage for q[4]
h q[4];

// final swaps (bit-reversal)
swap q[0], q[4];
swap q[1], q[3];
// q[2] stays in place
