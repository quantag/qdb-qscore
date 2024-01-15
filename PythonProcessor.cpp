#include "PythonProcessor.h"

#include "Utils.h"
#include "Log.h"

PythonProcessor::PythonProcessor() {
}

PythonProcessor::~PythonProcessor() {
}

std::string PythonProcessor::parsePythonToOpenQASM(const std::string& sourceCode) {
	LOGI("%s", sourceCode.c_str());

	Utils::parseSourcePerLines(sourceCode, sourceLines);
	Utils::logSource(sourceLines);

//	this->removeComments();
	this->removeAllPrints();
//	this->removeAllByWord("IBMQ");
//	this->removeAllByWord("provider");
//	this->removeAllByWord("job");
//	this->removeAllByWord("draw");

	std::vector<int> linesWithQuantumCircuit;
	findAllQuantumCircuitDeclarations(linesWithQuantumCircuit);

	if (!linesWithQuantumCircuit.empty()) {
		LOGI("Found QuantumCircuits at lines: %s", Utils::vectorToString(linesWithQuantumCircuit).c_str());

		for (int line : linesWithQuantumCircuit) {
			std::string qcName = getQuantumCircuitName(line);
			LOGI("QuantumCircuit name at line %d is '%s'", line, qcName.c_str());

			int lastLine = findLastUsage(qcName);
			if (lastLine > 0) {
				LOGI("Last usage of QC '%s' on line %d", qcName.c_str(), lastLine);
				this->sourceLines.insert(sourceLines.begin() + lastLine + 1, "print(qasm2.dumps("+ qcName +"))");
			}
		}
	}
	else {
		LOGI("No QuantumCircuit declarations found");
	}

	if (!importPresent("qiskit", "qasm2"))
		addImport("qiskit", "qasm2"); // "from qiskit import qasm2\n" + sourceCode;

	std::string updatedSource = combineVector(this->sourceLines);
	LOGI("Updated sources:\n%s", updatedSource.c_str());

	std::string out = Utils::executePythonCode(updatedSource);
	LOGI("%s", out.c_str());

	return out;
}

std::string PythonProcessor::combineVector(const std::vector<std::string>& lines) {
	std::string res = "";
	for (const std::string& line : lines) {
		res += line + "\n";
	}
	return res;
}

int PythonProcessor::findLastUsage(const std::string& item) {
	std::string str = item + ".";
	for (int i = (int)this->sourceLines.size() - 1; i >= 0; i--) {
		std::string line = this->sourceLines.at(i);

		if (line.find(str) != std::string::npos)
			return i;
	}
	return -1;
}

std::string PythonProcessor::getQuantumCircuitName(int line) {
	std::string data = this->sourceLines.at(line);
	std::vector<std::string> items = Utils::tokenize(data, "=");
	if (items.size() > 1) {
		std::string res = items.at(0);
		Utils::trim(res);
		return res;
	}
	return "";
}

void PythonProcessor::findAllQuantumCircuitDeclarations(std::vector<int>& result) {
	int n = 0;
	for (std::string& line : this->sourceLines) {
		if (line.find("QuantumCircuit") != std::string::npos && line.find("import") == std::string::npos) {
			result.push_back(n);
		}
		n++;
	}
}

void PythonProcessor::addImport(const std::string& module, const std::string& unit) {
	sourceLines.insert(sourceLines.begin(), "from " + module + " import " + unit);
}

bool PythonProcessor::importPresent(const std::string& module, const std::string& unit) {
	for (std::string& item : sourceLines) {
		if (item.find("import") != std::string::npos) {
			// from qiskit import qasm2
			std::vector<std::string> tokens = Utils::tokenize(item, " ");
			if (tokens.size() == 4) {
				if (tokens[0].compare("from") == 0 && tokens[2].compare("import") == 0
					&& tokens[1].compare(module) == 0) {
					// unit might be in a,b,c

					std::vector<std::string> units = Utils::tokenize(tokens[3], ",");
					for (std::string& itemUnit : units) {
						if (itemUnit.compare(unit) == 0)
							return true;
					}
				}
			}
		}
	}
	return false;
}

void PythonProcessor::removeAllByWord(const std::string& wrd) {
	auto it = std::remove_if(sourceLines.begin(), sourceLines.end(),
		[&](const std::string& line) {
			return !validateLine(line, wrd);
		});

	sourceLines.erase(it, sourceLines.end());
}

void PythonProcessor::removeAllPrints() {
	removeAllByWord("print");
}

bool PythonProcessor::validateLine(const std::string& line, const std::string& wrd) {
	if (line.find(wrd.c_str()) != std::string::npos && line.find("import") == std::string::npos)
		return false;

	return true;
}

void PythonProcessor::removeComments() {
//	Utils::logSource(this->sourceLines);

	std::vector<int> linesToRemove;
	for (int i = 0; i < this->sourceLines.size(); i++) {
		if (isOneLineCommentLine(sourceLines.at(i)))
			linesToRemove.push_back(i);
	}
	LOGI("single comment lines to remove %s",	Utils::vectorToString(linesToRemove).c_str());
	deleteLines(linesToRemove);
//	Utils::logSource(this->sourceLines);

	linesToRemove.clear();
	bool commentLine = false;
	for (int i = 0; i < this->sourceLines.size(); i++) {
		if (isMultiLineComment(sourceLines.at(i))) {
			commentLine = !commentLine;

			if(!commentLine) // last comment line
				linesToRemove.push_back(i);

		}
		if(commentLine)
			linesToRemove.push_back(i);
	}
	LOGI("multi comment lines to remove %s", Utils::vectorToString(linesToRemove).c_str());
	deleteLines(linesToRemove);
//	Utils::logSource(this->sourceLines);
}

int PythonProcessor::isMultiLineComment(const std::string& line) {
	if (line.find("\"\"\"") != std::string::npos)
		return 1;
	if (line.find("'''") != std::string::npos)
		return 1;

	return 0;
}

int PythonProcessor::isOneLineCommentLine(const std::string& line) {
	if (line.empty())
		return 1;

	if (line.at(0) == '#')
		return 1;

	return 0;
}

void PythonProcessor::deleteLines(const std::vector<int>& lines) {
	for (int i = (int)( lines.size() - 1 ); i >= 0; i--) {
		sourceLines.erase(sourceLines.begin() + lines.at(i));
	}
}