#pragma once

#include "PythonProcessor.h"

class QiskitProcessor : public PythonProcessor {
public:
	QiskitProcessor();
	virtual ~QiskitProcessor();

protected:
	virtual void findAllQuantumCircuitDeclarations(std::vector<int>& result);
	virtual std::string parsePythonToOpenQASM(const std::string& sourceCode);

};
