OPENQASM 2.0;
include "qelib1.inc";
qreg q[20];
creg c[20];
x q[0]; 
x q[2];
barrier q;
h q[0];
cu1(pi/2) q[1],q[0];
h q[1];
cu1(pi/4) q[2],q[0];
cu1(pi/2) q[2],q[1];
h q[2];
cu1(pi/8) q[3],q[0];
cu1(pi/4) q[3],q[1];
cu1(pi/2) q[3],q[2];
h q[3];
cu1(pi/2) q[4],q[3];
h q[4];
cu1(pi/2) q[5],q[4];
h q[5];
cu1(pi/2) q[6],q[5];
h q[6];
cu1(pi/2) q[7],q[6];
h q[7];
cu1(pi/2) q[8],q[7];
h q[8];
cu1(pi/2) q[9],q[8];
h q[9];
cu1(pi/2) q[10],q[9];
h q[10];
cu1(pi/2) q[11],q[10];
h q[11];
cu1(pi/2) q[12],q[11];
h q[12];
cu1(pi/2) q[13],q[12];
h q[13];
cu1(pi/2) q[14],q[13];
h q[14];
cu1(pi/2) q[15],q[14];
h q[15];
cu1(pi/2) q[16],q[15];
h q[16];
cu1(pi/2) q[17],q[16];
h q[17];
cu1(pi/2) q[18],q[17];
h q[18];
cu1(pi/2) q[19],q[18];
h q[19];
measure q -> c;