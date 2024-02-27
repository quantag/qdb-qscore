
#include "QiskitProcessor.h"
#include "Log.h"
#include "Utils.h"

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

std::string QiskitProcessor::parsePythonToOpenQASM(const std::string& sourceCode) {
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
				this->sourceLines.insert(sourceLines.begin() + lastLine + 1, "print(qasm2.dumps(" + qcName + "))");
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