#pragma once

#include "BaseQVM.h"

// Only compile if CUDA-Q is enabled
#ifdef ENABLE_CUDAQ

// Include necessary CUDA-Q headers
#include <cudaq.h>
#include <cudaq/algorithm.h>
#include <cudaq/builder.h>

class CudaQVM : public BaseQVM {
public:
    CudaQVM();
    CudaQVM(ConfigLoader* cfg);
    ~CudaQVM();

    virtual int loadSourceCode(const std::string& fileName, const std::string& sessionId, LaunchStatus& status);
    virtual int run(const std::string& fileName, const std::string& sessionId, LaunchStatus& status);
    virtual int debug(const std::string& fileName, const std::string& sessionId, LaunchStatus& status);

    std::string getQVMName();
    virtual double stepForward();

private:
    // CUDA-Q specific members
    std::unique_ptr<cudaq::kernel_builder> kernel; // The quantum kernel built from source
    cudaq::kernel_builder* get_kernel();           // Helper to get the kernel

    cudaq::sample_result sampleResult;             // Results from sampling
    cudaq::state stateResult;                      // Results from state simulation

    // Execution mode: 0 = sample (default), 1 = state, 2 = observe
    int executionMode = 0;

    // For debug/step-through execution
    std::vector<cudaq::instruction>::iterator currentInstruction;
    std::unique_ptr<cudaq::simulation_state> simState;
    bool isDebugMode = false;

    // Helper functions
    void resetExecution();
    int executeFullCircuit(LaunchStatus& status);
    int executeSingleStep(LaunchStatus& status);
};

#endif