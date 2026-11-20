/*
 * Copyright (c) 2024 Quantag IT Solutions GmbH
 *
 * This source code is licensed under the MIT license found in the
 * LICENSE file in the root directory of this source tree.
 */

#pragma once

#include <string>
#include "../interfaces/ifrontend.h"

class ConfigLoader;

// interface to QVM
class IQVM {
public:
	virtual int loadSourceCode(const std::string& fileName, const std::string& sessionId, LaunchStatus& status) = 0;
	virtual int run(const std::string& fileName, const std::string& sessionId, LaunchStatus& status) = 0;
	virtual int debug(const std::string& fileName, const std::string& sessionId, LaunchStatus& status) = 0;

	virtual std::string getQVMName() = 0;

	virtual int getSourceLines() = 0;
	virtual double stepForward() = 0;
	virtual void setWSSession(WSSession* wsSession) = 0;

	// true when the QVM steps circuit instructions and reports their source lines
	// (CUDA-Q C++); false for the line-by-line mode of OpenQASM and Python
	virtual bool stepsByInstruction() const {
		return false;
	}

	// Disassembly view: index (0-based, circuit order) of the next instruction to
	// execute, or -1 when unknown
	virtual int getCurrentInstructionIndex() const {
		return -1;
	}
	// Source line (1-based) of instruction idx, 0 when unknown
	virtual int getInstructionSourceLine(int idx) const {
		(void)idx;
		return 0;
	}
	// Index in getSourcePerLines() (the QASM that runs) of every instruction, in order
	virtual std::vector<int> getInstructionQasmLines() const {
		return std::vector<int>();
	}

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
	std::string _errorMessage;

	ConfigLoader* getConfig() {
		return cfg;
	}

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
	ConfigLoader* cfg;

};