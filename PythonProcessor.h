#pragma once

#include <vector>
#include <string>

#include "Typedefs.h"
#include "RestClient.h"

#define SERVER_IMAGE_FOLDER		"/var/dap/images/"
#define BRIDGE_VAR				"code777"

class PythonProcessor {
public:
	PythonProcessor();
	PythonProcessor(PythonFramework fw);
	virtual ~PythonProcessor();

	virtual ScriptExecResult parsePythonToOpenQASM(const std::string& sourceCode, const std::string& sessionId) = 0;
	int findMathImport();

	PythonFramework getFramework() const {
		return framework;
	}
	ScriptExecResult renderOpenQASMCircuit(const std::string& sourceCode, const std::string& sessionId);

protected:
	std::vector<std::string> sourceLines;
	bool importPresent(const std::string& module, const std::string& unit);
	void addImport(const std::string& module, const std::string& unit);
	virtual void findAllQuantumCircuitDeclarations(std::vector<int>& result) = 0;
	std::string getQuantumCircuitName(int line);
	int findLastUsage(const std::string& item);
	void removeAllPrints();
	void removeAllByWord(const std::string& word);

	bool validateLine(const std::string& line, const std::string& wrd);
	void removeComments();
	void deleteLines(const std::vector<int>& lines);
	int isOneLineCommentLine(const std::string& line);
	int isMultiLineComment(const std::string& line);
	int findLastImportLine();
	std::string getPreSpaces(int line);

	PythonFramework framework;
	RestClient restClient;
};

