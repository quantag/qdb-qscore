
#include "TketProcessor.h"

TketProcessor::TketProcessor() {

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