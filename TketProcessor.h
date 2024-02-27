#pragma once

#include "PythonProcessor.h"

class TketProcessor : public PythonProcessor {
public:
	TketProcessor();
	virtual ~TketProcessor();

protected:
	void findAllQuantumCircuitDeclarations(std::vector<int>& result);
	virtual std::string parsePythonToOpenQASM(const std::string& sourceCode);

};
