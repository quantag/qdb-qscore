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
	QiskitProcessor(ConfigLoader* cfg);
	virtual ~QiskitProcessor();

	// Full Python source sent to the executor (QiskitBridge.h and the call with the
	// base64-encoded program and the path of the circuit image)
	static std::string buildBridgeSource(const std::string& sourceCode, const std::string& imagePath,
		const std::string& projectRoot = "", const std::string& programPath = "");

protected:
	virtual void findAllQuantumCircuitDeclarations(std::vector<int>& result);
	virtual ScriptExecResult parsePythonToOpenQASM(const std::string& sourceCode, const std::string& sessionId, const std::string& venv);


};
