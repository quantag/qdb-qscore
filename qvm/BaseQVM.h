
#pragma once

#include "../interfaces/iqvm.h"

class ConfigLoader;
class PythonProcessor;
class IFrontend;

class BaseQVM : public IQVM {
public:
	void updateProcessor(CodeFramework framework);
	int getSourceLines();
	virtual bool stepsByInstruction() const {
		return !gateSourceLines.empty();
	}
	virtual int getInstructionSourceLine(int idx) const {
		return idx >= 0 && idx < static_cast<int>(gateSourceLines.size()) ? gateSourceLines[idx] : 0;
	}
	virtual std::vector<int> getInstructionQasmLines() const;
	void setWSSession(WSSession* wsSession);

	int prepareSource(const std::string& fileName,
		const std::string& sessionId,
		LaunchStatus& status,
		std::string& preparedSource);

	virtual int run(const std::string& code,
		const std::string& path,
		LaunchStatus& status) = 0;

	std::string getVenvIfPresent(const std::string& fileName);
	std::string getProjectVenv(const std::string& fileName);

	static bool isPythonCommentLine(const std::string& rawLine);

protected:
	PythonProcessor* processor;
	IFrontend* frontend;

	std::string venv;
	static bool isExecutableQasmLine(const std::string& rawLine);

	// mapping from original source code to compiled openqasm
	std::vector<std::vector<int>> sourceToQasmLines;
	void generateCodeMapping(const std::string& preparedSource,
		CodeType codeType);
	void generateOpenQASMCodeMapping(const std::string& preparedSource);
	void generatePythonCodeMapping(const std::string& preparedSource);

	// gateSourceLines holds the source line of every executable QASM instruction in
	// circuit order; when it is not empty the QVM steps instruction by instruction.
	// CUDA-Q C++: the file is translated to OpenQASM by an external tool (cpp.qasm.tool)
	// that reports the source line of every QASM line. Qiskit: the Python processor
	// appends those lines to the QASM as a comment (QASM_LINES_MARKER).
	std::vector<int> gateSourceLines;
	int translateCppSource(const std::string& file, LaunchStatus& status, std::string& preparedSource);
	void setGateSourceLines(const std::string& qasm, const std::vector<int>& qasmLineSources);
	bool takePythonSourceLines(std::string& preparedSource);
	void generateInstructionLineMapping();

	void logCodeMapping() const;
};
