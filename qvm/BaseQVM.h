
#pragma once

#include "../interfaces/iqvm.h"

class ConfigLoader;
class PythonProcessor;
class IFrontend;

class BaseQVM : public IQVM {
public:
	void updateProcessor(CodeFramework framework);
	int getSourceLines();
	void setWSSession(WSSession* wsSession);

	int prepareSource(const std::string& fileName,
		const std::string& sessionId,
		LaunchStatus& status,
		std::string& preparedSource);

	virtual int run(const std::string& code,
		const std::string& path,
		LaunchStatus& status) = 0;

	std::string getVenvIfPresent(const std::string& fileName);

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

	void logCodeMapping() const;
};
