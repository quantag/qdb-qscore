OPENQASM 2.0;
include "qelib1.inc";
qreg q[28];
creg c[28];
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
cu1(pi/2) q[20],q[19];
h q[20];
cu1(pi/2) q[21],q[20];
h q[21];
cu1(pi/2) q[22],q[21];
h q[22];
cu1(pi/2) q[23],q[22];
h q[23];
cu1(pi/2) q[24],q[23];
h q[24];
cu1(pi/2) q[25],q[24];
h q[25];
cu1(pi/2) q[26],q[25];
h q[26];
cu1(pi/2) q[27],q[26];
h q[27];
measure q -> c;