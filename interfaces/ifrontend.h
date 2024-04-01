#pragma once

#include <string>
#include <vector>

#include "../Typedefs.h"

typedef std::vector< std::vector<complexNumber>>  matrix2d;

// current state show on frontent
struct FrontState {
	int currentLine;

	std::vector<complexNumber> states;
	std::string code;
//	matrix2d densityMatrix;
};


class WSSession;
// interface to web frontend
class IFrontend {
public:
	virtual int loadCode(const std::string &sourceCode) = 0;
	virtual int updateState(const FrontState &state) = 0;

	virtual void setWSSession(WSSession* ws) {
		this->wsSession = ws;
	}

protected:
	WSSession* wsSession;
};