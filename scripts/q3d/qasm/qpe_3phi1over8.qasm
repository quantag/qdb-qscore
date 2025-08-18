OPENQASM 2.0;
include "qelib1.inc";

// counting: cnt[0]=LSB ... cnt[2]=MSB
qreg cnt[3];
qreg tgt[1];
creg out[3];

// Prepare target |1>
x tgt[0];

// Put counting in superposition
h cnt[0]; h cnt[1]; h cnt[2];

// Apply controlled-U^{2^k} with U = phase on |1>, =1/8
// cu1(theta) control, target
cu1(pi/4)  cnt[0], tgt[0];  // 2 * 1/8
cu1(pi/2)  cnt[1], tgt[0];  // doubled
cu1(pi)    cnt[2], tgt[0];  // doubled again

// Inverse QFT on cnt[0..2] (with final swaps for natural order)
h cnt[2];
cu1(-pi/2) cnt[2], cnt[1];
cu1(-pi/4) cnt[2], cnt[0];

h cnt[1];
cu1(-pi/2) cnt[1], cnt[0];

h cnt[0];

// swap to undo bit-reversal
swap cnt[0], cnt[2];

barrier cnt;
measure cnt -> out;
