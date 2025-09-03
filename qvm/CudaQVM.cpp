#include "CudaQVM.h"

#ifdef ENABLE_CUDAQ

#include "../Log.h"
#include "../Utils.h"
#include "../ConfigLoader.h"
#include "../WebFrontend.h"
#include "../QiskitProcessor.h"
#include "../TketProcessor.h"

CudaQVM::CudaQVM() {
    this->frontend = new WebFrontend();
    this->sourceCodeParsed = 0;
    processor = new QiskitProcessor();
    this->cfg = nullptr;
    resetExecution();
}

CudaQVM::CudaQVM(ConfigLoader* cfg) {
    this->frontend = new WebFrontend();
    this->sourceCodeParsed = 0;
    processor = new QiskitProcessor();
    this->cfg = cfg;
    resetExecution();
}

CudaQVM::~CudaQVM() {
    SAFE_DELETE(frontend);
    delete processor;
    // unique_ptr and CUDA-Q objects will handle their own cleanup
}

void CudaQVM::resetExecution() {
    kernel.reset();
    sampleResult = cudaq::sample_result();
    stateResult = cudaq::state();
    executionMode = 0;
    currentInstruction = std::vector<cudaq::instruction>::iterator();
    simState.reset();
    isDebugMode = false;
}

int CudaQVM::loadSourceCode(const std::string& fileName, const std::string& sessionId, LaunchStatus& status) {
    LOGI("[CudaQVM] Loading source from: %s", fileName.c_str());

    // === Copy logic from QppQVM::loadSourceCode up to the point you have OpenQASM ===
    // (file lookup, detect code type, processor->parsePythonToOpenQASM, etc.)

    try {
        kernel = std::make_unique<cudaq::kernel_builder>(
            cudaq::from_openqasm(this->sourceCode)
        );
        this->nQubits = kernel->get_num_qubits();
        this->sourceCodeParsed = 1;

        Utils::parseSourcePerLines(this->sourceCode, this->sourceCodePerLines);
        frontend->loadCode(this->sourceCode);

        return ERR_OK;
    }
    catch (const std::exception& e) {
        status.errorMessage = std::string("CUDA-Q Kernel Build Error: ") + e.what();
        this->sourceCodeParsed = 0;
        return ERR_PARSEERROR;
    }
}


double CudaQVM::stepForward() {
    return 0.0;
}

std::string CudaQVM::getQVMName() {
    return "CUDA-Q (CPU backend)";
}


int CudaQVM::run(const std::string& fileName, const std::string& sessionId, LaunchStatus& status) {
    LOGI("[CudaQVM] Run called for: %s", fileName.c_str());

    int loadRet = loadSourceCode(fileName, sessionId, status);
    if (loadRet != ERR_OK || !this->sourceCodeParsed) {
        LOGE("Failed to load or parse source code for execution.");
        return (loadRet == ERR_OK) ? ERR_PARSEERROR : loadRet; // Ensure an error is returned
    }

    return executeFullCircuit(status);
}

int CudaQVM::executeFullCircuit(LaunchStatus& status) {
    try {
        auto start = std::chrono::steady_clock::now();

        // Sample the kernel execution (default behavior)
        sampleResult = cudaq::sample(*kernel);
        // Alternatively, one could use cudaq::state(*kernel) to get the state vector

        auto stop = std::chrono::steady_clock::now();
        auto duration = std::chrono::duration<double>(stop - start);
        double timeSec = duration.count();

        LOGI("CUDA-Q execution finished. Time: %.6f sec", timeSec);

        // Prepare result for the frontend - Convert sample_result to a state representation if needed
        // This part is complex because sample_result is statistical. You might want to show counts.
        // For simplicity here, we'll just signal success. A real implementation would format the results.
        currentState.executionTime = timeSec;
        currentState.message = "Execution complete. Sample results available.";
        // You would need to add a member like `sampleResults` to QState and populate it here
        frontend->updateState(currentState);

        return ERR_OK;

    }
    catch (const std::exception& e) {
        LOGE("Error during CUDA-Q execution: %s", e.what());
        status.errorMessage = std::string("CUDA-Q Execution Error: ") + e.what();
        return ERR_RUNTIMEERROR;
    }
}


int CudaQVM::debug(const std::string& fileName, const std::string& sessionId, LaunchStatus& status) {
    LOGI("[CudaQVM] Debug called for: %s", fileName.c_str());

    int loadRet = loadSourceCode(fileName, sessionId, status);
    if (loadRet != ERR_OK || !this->sourceCodeParsed) {
        LOGE("Failed to load or parse source code for debugging.");
        return (loadRet == ERR_OK) ? ERR_PARSEERROR : loadRet;
    }

    isDebugMode = true;

    try {
        // Initialize the simulation state for stepping
        // Note: CUDA-Q's simulation state API might be less direct than QPP's iterator.
        // This is a conceptual approach. The exact API might differ.
        simState = std::make_unique<cudaq::simulation_state>(*kernel);
        auto& instructions = simState->get_instructions(); // Hypothetical method
        currentInstruction = instructions.begin();

        LOGI("CUDA-Q debug session initialized. Instructions: %lu", instructions.size());
        return ERR_OK;

    }
    catch (const std::exception& e) {
        LOGE("Error initializing CUDA-Q debug session: %s", e.what());
        status.errorMessage = std::string("CUDA-Q Debug Init Error: ") + e.what();
        isDebugMode = false;
        return ERR_RUNTIMEERROR;
    }
}

double CudaQVM::stepForward() {
    if (!isDebugMode || !simState || currentInstruction == simState->get_instructions().end()) {
        LOGI("StepForward called but not in debug mode or execution finished.");
        return 0.0;
    }

    try {
        auto start = std::chrono::steady_clock::now();

        // Execute the single instruction (Conceptual)
        simState->execute_instruction(*currentInstruction); // Hypothetical method
        ++currentInstruction;

        auto stop = std::chrono::steady_clock::now();
        auto duration = std::chrono::duration<double>(stop - start);

        // Get the current state vector after the step
        // stateResult = simState->get_state(); // Hypothetical method
        // currentState.states = convertCudaQStateToStdVector(stateResult); // Needs implementation

        this->currentState.currentLine = Utils::getNextLine(this->currentState.currentLine - 1, this->originalParsedCode, 2) + 1;
        frontend->updateState(currentState);

        LOGI("Step executed. Time: %.6f sec", duration.count());
        return duration.count();

    }
    catch (const std::exception& e) {
        LOGE("Error executing step: %s", e.what());
        return 0.0;
    }
}

std::string CudaQVM::getQVMName() {
    // Get CUDA-Q version at runtime if possible, or hardcode based on linked version
    return "NVIDIA CUDA-Q"; // Consider enhancing this
}
#endif