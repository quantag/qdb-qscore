/*
 * Copyright (c) 2024 Quantag IT Solutions GmbH
 *
 * This source code is licensed under the MIT license found in the
 * LICENSE file in the root directory of this source tree.
 */

#pragma once

#include "PythonProcessor.h"

// CUDA-Q (Python) programs: the program is executed in the project's venv by the
// Python executor and the kernel to debug is converted to OpenQASM 2.0 (see CudaQBridge.h).
class CudaQProcessor : public PythonProcessor {
public:
	CudaQProcessor(ConfigLoader* cfg);
	virtual ~CudaQProcessor();

	// Name of the kernel passed to cudaq.sample/observe/run/draw/get_state, or "" if none
	static std::string findKernelHint(const std::string& sourceCode);

	// Full Python source sent to the executor (prologue + program + conversion)
	static std::string buildBridgeSource(const std::string& sourceCode);

protected:
	virtual void findAllQuantumCircuitDeclarations(std::vector<int>& result);
	virtual ScriptExecResult parsePythonToOpenQASM(const std::string& sourceCode, const std::string& sessionId, const std::string& venv);
};
