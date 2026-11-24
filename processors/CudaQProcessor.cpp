/*
 * Copyright (c) 2024 Quantag IT Solutions GmbH
 *
 * This source code is licensed under the MIT license found in the
 * LICENSE file in the root directory of this source tree.
 */

#include "CudaQProcessor.h"
#include "CudaQBridge.h"

#include "../Log.h"
#include "../Utils.h"
#include "../ConfigLoader.h"

#include <regex>
#include <sstream>

CudaQProcessor::CudaQProcessor(ConfigLoader* cfg) : PythonProcessor(eCUDAQ, cfg) {
}

CudaQProcessor::~CudaQProcessor() {
}

void CudaQProcessor::findAllQuantumCircuitDeclarations(std::vector<int>& result) {
	int n = 0;
	for (std::string& line : this->sourceLines) {
		if (line.find("@cudaq.kernel") != std::string::npos) {
			result.push_back(n);
		}
		n++;
	}
}

std::string CudaQProcessor::findKernelHint(const std::string& sourceCode) {
	static const std::regex callRe(
		R"(cudaq\.(?:sample|sample_async|observe|observe_async|run|run_async|draw|get_state|get_state_async|translate)\(\s*([A-Za-z_][A-Za-z0-9_]*))");
	std::smatch m;
	if (std::regex_search(sourceCode, m, callRe)) {
		return m[1].str();
	}
	return "";
}

static void replaceToken(std::string& text, const std::string& token, const std::string& value) {
	size_t pos = text.find(token);
	if (pos != std::string::npos) {
		text.replace(pos, token.size(), value);
	}
}

std::string CudaQProcessor::buildBridgeSource(const std::string& sourceCode,
		const std::string& projectRoot, const std::string& programPath) {
	// Split into lines, keeping every line (empty lines and comments matter for Python)
	std::vector<std::string> lines;
	std::istringstream in(sourceCode);
	std::string line;
	while (std::getline(in, line)) {
		if (!line.empty() && line.back() == '\r') {
			line.pop_back();
		}
		lines.push_back(line);
	}

	// "from __future__" imports must stay the first statements of the file
	size_t insertAt = 0;
	for (size_t i = 0; i < lines.size(); i++) {
		if (lines[i].rfind("from __future__ import", 0) == 0) {
			insertAt = i + 1;
		}
	}

	std::string hint = findKernelHint(sourceCode);

	std::string out;
	for (size_t i = 0; i < insertAt; i++) {
		out += lines[i] + "\n";
	}
	std::string prologue = CUDAQ_PROLOGUE;
	std::string programDir;
	size_t slash = programPath.find_last_of("/\\");
	if (slash != std::string::npos) {
		programDir = programPath.substr(0, slash);
	}
	replaceToken(prologue, "__QS_PROJECT_ROOT__", pyLiteral(projectRoot));
	replaceToken(prologue, "__QS_PROGRAM_DIR__", pyLiteral(programDir));
	out += prologue;
	for (size_t i = insertAt; i < lines.size(); i++) {
		out += lines[i] + "\n";
	}
	out += "\n_QS_KERNEL_HINT = " + (hint.empty() ? std::string("None") : "'" + hint + "'") + "\n";
	out += CUDAQ_EPILOGUE;

	// Program lines after the prologue are shifted by its length; CUDAQ_LINES undoes that
	size_t prologueLines = 0;
	for (const char* c = CUDAQ_PROLOGUE; *c; c++) {
		if (*c == '\n') prologueLines++;
	}
	out += "_QS_LINE_SHIFT = (" + std::to_string(insertAt) + ", " + std::to_string(prologueLines) + ")\n";
	out += CUDAQ_LINES;
	out += CUDAQ_RESTORE_STDOUT;
	return out;
}

ScriptExecResult CudaQProcessor::parsePythonToOpenQASM(const std::string& sourceCode, const std::string& sessionId, const std::string& venv) {
	LOGI("sessionId=[%s] venv=[%s] kernel hint=[%s]", sessionId.c_str(), venv.c_str(), findKernelHint(sourceCode).c_str());

	Utils::parseSourcePerLines(sourceCode, sourceLines);

	LOGI("project root=[%s] program=[%s]", projectRoot.c_str(), programPath.c_str());
	std::string updatedSource = buildBridgeSource(sourceCode, projectRoot, programPath);
	LOGD("Updated sources:\n%s", updatedSource.c_str());

	restClient.setEndpoint(cfg->getPythonExecutorEndpoint().c_str());
	ScriptExecResult result = restClient.execCode(updatedSource, venv);
	LOGI("result status: %d", result.status);
	return result;
}
