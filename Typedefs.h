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

struct CommandResult {
	std::string output;
	int exitstatus;

	/*friend std::ostream& operator<<(std::ostream& os, const CommandResult& result) {
		os << "command exitstatus: " << result.exitstatus << " output: " << result.output;
		return os;
	}
	bool operator==(const CommandResult& rhs) const {
		return output == rhs.output &&
			exitstatus == rhs.exitstatus;
	}
	bool operator!=(const CommandResult& rhs) const {
		return !(rhs == *this);
	}*/
};

enum class EventEnum { BreakpointHit, Stepped, Paused };

#include <functional>
using EventHandler = std::function<void(EventEnum)>;


#define SAFE_DELETE(x)	if(x){delete x;x=0;}
#define ASSERT(x)		if(x){return x;}
