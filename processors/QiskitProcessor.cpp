/*
 * Copyright (c) 2024 Quantag IT Solutions GmbH
 *
 * This source code is licensed under the MIT license found in the
 * LICENSE file in the root directory of this source tree.
 */


#include "QiskitProcessor.h"
#include "QiskitBridge.h"
#include "../Log.h"
#include "../Utils.h"
#include "../RestClient.h"
#include "../ConfigLoader.h"

QiskitProcessor::QiskitProcessor(ConfigLoader* cfg) : PythonProcessor(eQiskit, cfg) {
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

std::string QiskitProcessor::buildBridgeSource(const std::string& sourceCode, const std::string& imagePath) {
	std::string out = QISKIT_BRIDGE;
	out += "\n" + std::string(BRIDGE_VAR) + " = _qs_qiskit_debug('" + Utils::encode64(sourceCode) + "', '" + imagePath + "')\n";
	return out;
}

ScriptExecResult QiskitProcessor::parsePythonToOpenQASM(const std::string& sourceCode, const std::string& sessionId, const std::string& venv) {
	LOGI("sessionId=[%s] venv=[%s]", sessionId.c_str(), venv.c_str());

	Utils::parseSourcePerLines(sourceCode, sourceLines);
	Utils::logSource(sourceLines);

	// The program runs unchanged inside the bridge (no removed or inserted lines), so
	// the lines the bridge reports are the lines of the file.
	std::string updatedSource = buildBridgeSource(sourceCode, std::string(SERVER_IMAGE_FOLDER) + sessionId + ".png");

	restClient.setEndpoint( cfg->getPythonExecutorEndpoint().c_str() );
	ScriptExecResult  result = restClient.execCode(updatedSource, venv);
	LOGI("result status: %d", result.status);

	return result;
}
