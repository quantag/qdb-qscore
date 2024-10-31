#pragma once

#include <string>
#include "../interfaces/ifrontend.h"

// interface to QVM
class IQVM {
public:
	virtual int loadSourceCode(const std::string& fileName, const std::string& sessionId, std::string& errorMessage) = 0;
	virtual int run(const std::string& fileName, const std::string& sessionId) = 0;
	virtual int debug(const std::string& fileName, const std::string& sessionId) = 0;

	virtual std::string getQVMName() = 0;

	virtual int getSourceLines() = 0;
	virtual long long stepForward() = 0;
	virtual void setWSSession(WSSession* wsSession) = 0;

	virtual int getCurrentLine() const {
		return currentState.currentLine;
	}
	virtual void setCurrentLine(int line) {
		this->currentState.currentLine = line;
	}

	virtual FrontState& getCurrentState() {
		return this->currentState;
	}

	virtual size_t getQubitsCount() const {
		return this->nQubits;
	}

	virtual int isSourceCodeParsed() const {
		return sourceCodeParsed;
	}

	const std::string& getSourceCode() const {
		return sourceCode;
	}

	const std::vector<std::string>& getSourcePerLines() {
		return sourceCodePerLines;
	}
	std::string errorMessage;

protected:
	std::string sourceCode;

	// original not changed source code received by VM.
	// we need to track currentLine on this code
	// can be OpenQASM or Python code
	std::string originalSourceCode;
	std::vector<CodeLine> originalParsedCode;
	std::vector<std::string> sourceCodePerLines;

	FrontState currentState;
	size_t nQubits;

	int sourceCodeParsed;
};