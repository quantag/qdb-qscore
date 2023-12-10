#pragma once

#include <string>
#include <vector>

// z = a + i*b
struct complexNumber {
	double a;
	double b;
};


typedef std::vector< std::vector<complexNumber>>  matrix2d;

// current state show on frontent
struct FrontState {
	int currentLine;

	std::vector<complexNumber> states;
	matrix2d densityMatrix;
};


class WSServer;
// interface to web frontend
class IFrontend {
public:
	virtual int loadCode(const std::string &sourceCode) = 0;
	virtual int updateState(const FrontState &state) = 0;

	virtual void setWSServer(WSServer* ws) {
		this->wsServer = ws;
	}

protected:
	WSServer* wsServer;
};