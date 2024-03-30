
#include "QiskitProcessor.h"
#include "Log.h"
#include "Utils.h"

#include "RestClient.h"

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

std::string QiskitProcessor::parsePythonToOpenQASM(const std::string& sourceCode, const std::string& sessionId) {
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
				this->sourceLines.insert(sourceLines.begin() + lastLine + 1, "code777=qasm2.dumps(" + qcName + ")");
				this->sourceLines.insert(sourceLines.begin() + lastLine + 1, "" + qcName + ".draw(output='mpl', filename='"+sessionId+".png')");
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

//	std::string out = Utils::executePythonCode(updatedSource, eQiskit);
	std::string out = restClient.execPythonCode(updatedSource);
	LOGI("output: '%s'", out.c_str());

	return out;
}