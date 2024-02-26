
#include "QiskitProcessor.h"

QiskitProcessor::QiskitProcessor() {

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