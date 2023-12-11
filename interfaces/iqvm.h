#pragma once

#include <string>
#include "../interfaces/ifrontend.h"

// interface to QVM
class IQVM {
public:
	virtual int loadSourceCode(const std::string& fileName) = 0;

	virtual int run(const std::string& fileName) = 0;
	virtual int debug(const std::string& fileName) = 0;

	virtual int getSourceLines() = 0;
	virtual void stepForward() = 0;

	virtual int getCurrentLine() const {
		return currentState.currentLine;
	}
	virtual void setCurrentLine(int line) {
		this->currentState.currentLine = line;
	}

	virtual FrontState& getCurrentState() {
		return currentState;
	}

protected:
	std::string sourceCode;
	FrontState currentState;
};