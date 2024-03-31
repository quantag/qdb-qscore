
#include "QiskitProcessor.h"
#include "Log.h"
#include "Utils.h"

#include "RestClient.h"

// where store generated circuit images on server

QiskitProcessor::QiskitProcessor() : PythonProcessor(eQiskit) {

}

QiskitProcessor::~QiskitProcessor() {

}

void QiskitProcessor::findAllQuantumCircuitDeclarations(std::vector<int>& result) {
	int n = 0;
	for (std::string& line : this->sourceLines) {
		if (line.find("QuantumCircuit") != std::string::npos && line.find("import") == std::string::npos) {
			result.push_back(n);
		}
		n++;
	}
}

ScriptExecResult QiskitProcessor::parsePythonToOpenQASM(const std::string& sourceCode, const std::string& sessionId) {
	LOGI("QiskitProcessor: '%s' [%s]", sourceCode.c_str(), sessionId.c_str());

	Utils::parseSourcePerLines(sourceCode, sourceLines);
	Utils::logSource(sourceLines);

	this->removeAllPrints();

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
				std::string spaces = getPreSpaces(lastLine);

				this->sourceLines.insert(sourceLines.begin() + lastLine + 1, spaces + "code777=qasm2.dumps(" + qcName + ")"); // if in function it will not work
				this->sourceLines.insert(sourceLines.begin() + lastLine + 1, spaces + qcName + std::string(".draw(output='mpl', filename='")+SERVER_IMAGE_FOLDER+sessionId+".png')");
			}
		}
	}
	else {
		LOGI("No QuantumCircuit declarations found");
	}

	if (!importPresent("qiskit", "qasm2")) {
		addImport("qiskit", "qasm2"); // "from qiskit import qasm2\n" + sourceCode;
	}

	LOGI("Updated sources:\n");
	Utils::logSource(sourceLines);
	std::string updatedSource = combineVector(this->sourceLines);

//	std::string out = Utils::executePythonCode(updatedSource, eQiskit);
	std::string out;
	ScriptExecResult  result = restClient.execPythonCode(updatedSource);
	LOGI("result status: %d", result.status);

	return result;
}