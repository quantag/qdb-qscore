#pragma once

// z = a + i*b
struct complexNumber {
	double a;
	double b;

	complexNumber() { a = 0.; b = 0.; }

	complexNumber(double real, double im) {
		this->a = real;
		this->b = im;
	}
};
