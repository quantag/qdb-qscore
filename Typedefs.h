#pragma once

// z = a + i*b
// TODO: use std::complex instead
struct complexNumber {
	double a;
	double b;

	complexNumber() { a = 0.; b = 0.; }

	complexNumber(double real, double im) {
		this->a = real;
		this->b = im;
	}
};

enum PythonFramework {
	eGeneric = 0,
	eQiskit = 1,
	eTket = 2
};

enum class CodeType {
	Python,
	OpenQASM,
	Unknown
};