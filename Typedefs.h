#pragma once

#include <string>
#include <functional>


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
	ePython,
	eOpenQASM,
	eUnknown
};

struct CommandResult {
	std::string output;
	int exitstatus;
};

enum class EventEnum { BreakpointHit, Stepped, Paused };
using EventHandler = std::function<void(EventEnum)>;


#define SAFE_DELETE(x)	if(x){delete x;x=0;}
#define ASSERT(x)		if(x){return x;}

struct ScriptExecResult {
	int status;
	std::string res;
	std::string err;
};

#define PYTHON_EXECUTER_ENDPONT_URL     "https://cryspprod3.quantag-it.com:444/api3/dec"
#define QUA_COMPILER_ENDPONT_URL		"https://cryspprod3.quantag-it.com:444/api4/compile"
#define QUA_EXECUTOR_ENDPONT_URL		"https://cryspprod3.quantag-it.com:444/api5/run"

struct CodeLine {
	std::string line;
	int type; // 0 = comment, 1 = info, 2 = executable
};

#define ERR_OK			0
#define ERR_NOFILE		1
#define ERR_DEMOFILE	2
#define ERR_PARSEERROR	3
