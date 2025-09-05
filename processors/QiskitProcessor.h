/*
 * Copyright (c) 2024 Quantag IT Solutions GmbH
 *
 * This source code is licensed under the MIT license found in the
 * LICENSE file in the root directory of this source tree.
 */

#pragma once

#include "PythonProcessor.h"

class QiskitProcessor : public PythonProcessor {
public:
	QiskitProcessor();
	virtual ~QiskitProcessor();

protected:
	virtual void findAllQuantumCircuitDeclarations(std::vector<int>& result);
	virtual ScriptExecResult parsePythonToOpenQASM(const std::string& sourceCode, const std::string& sessionId);


};
