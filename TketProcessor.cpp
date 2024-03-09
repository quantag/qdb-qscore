
#include "TketProcessor.h"

#include "Log.h"
#include "Utils.h"

TketProcessor::TketProcessor() : PythonProcessor(eTket) {

}

TketProcessor::~TketProcessor() {

}

/**
from pytket.circuit import Circuit
c = Circuit(3, 2)
*/
void TketProcessor::findAllQuantumCircuitDeclarations(std::vector<int>& result) {
	int n = 0;
	for (std::string& line : this->sourceLines) {
		if (line.find("Circuit") != std::string::npos && line.find("import") == std::string::npos) {
			result.push_back(n);
		}
		n++;
	}
}

std::string TketProcessor::parsePythonToOpenQASM(const std::string& sourceCode) {
	LOGI("%s", sourceCode.c_str());

	Utils::parseSourcePerLines(sourceCode, sourceLines);
	Utils::logSource(sourceLines);

	this->removeAllPrints();

	std::vector<int> linesWithQuantumCircuit;
	findAllQuantumCircuitDeclarations(linesWithQuantumCircuit);

	if (!linesWithQuantumCircuit.empty()) {
		LOGI("Found Circuits at lines: %s", Utils::vectorToString(linesWithQuantumCircuit).c_str());

		for (int line : linesWithQuantumCircuit) {
			std::string qcName = getQuantumCircuitName(line);
			LOGI("Circuit name at line %d is '%s'", line, qcName.c_str());

			int lastLine = findLastUsage(qcName);
			if (lastLine > 0) {
				LOGI("Last usage of QC '%s' on line %d", qcName.c_str(), lastLine);
				// qasm_str = circuit_to_qasm_str(circ, header="hqslib1")
				this->sourceLines.insert(sourceLines.begin() + lastLine + 1, "code777=circuit_to_qasm_str(" + qcName + ", header=\"hqslib1\")");
			}
		}
	}
	else {
		LOGI("No QuantumCircuit declarations found");
	}

	if (!importPresent("pytket.qasm", "circuit_to_qasm_str"))
		addImport("pytket.qasm", "circuit_to_qasm_str"); 

	std::string updatedSource = combineVector(this->sourceLines);
	LOGI("Updated sources:\n%s", updatedSource.c_str());

	std::string out = restClient.execPythonCode(updatedSource);
//	std::string out = Utils::executePythonCode(updatedSource, eTket);
	LOGI("%s", out.c_str());

	return out;
}