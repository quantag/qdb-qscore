#pragma once

#include <vector>
#include <string>

class PythonProcessor
{
public:
	PythonProcessor();
	virtual ~PythonProcessor();

	std::string parsePythonToOpenQASM(const std::string& sourceCode);
	static std::string combineVector(const std::vector<std::string>& lines);

private:
	std::vector<std::string> sourceLines;
	bool importPresent(const std::string& module, const std::string& unit);
	void addImport(const std::string& module, const std::string& unit);
	void findAllQuantumCircuitDeclarations(std::vector<int>& result);
	std::string getQuantumCircuitName(int line);
	int findLastUsage(const std::string& item);
	void removeAllPrints();

	bool validateLine(const std::string& line);

};

