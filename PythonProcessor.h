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

};

