#pragma once
#include "BaseQVM.h"

#ifdef ENABLE_CUDAQ

// CUDA-Q (headers layout differs by install; these two work with current SDKs)
#include <cudaq.h>
#include <cudaq/builder/kernel_builder.h>

#include <functional>
#include <regex>
#include <string>
#include <unordered_map>
#include <vector>

class ConfigLoader;
struct LaunchStatus;

class CudaQVM : public BaseQVM {
public:
    CudaQVM();
    explicit CudaQVM(ConfigLoader* cfg);
    ~CudaQVM();

    // IQVM
    int loadSourceCode(const std::string& fileName,
        const std::string& sessionId,
        LaunchStatus& status) override;

    // stubs (to be implemented next steps)
    int    run(const std::string&, const std::string&, LaunchStatus&) override { return ERR_OK; }
    int    debug(const std::string&, const std::string&, LaunchStatus&) override { return ERR_OK; }
    double stepForward() override { return 0.0; }

    std::string getQVMName() override { return "NVIDIA CUDA-Q"; }

private:
    using Op = std::function<void(cudaq::kernel_builder<>&,
        std::vector<cudaq::QuakeValue>&)>;


    std::vector<Op>  ops_;
    std::size_t      numQubits_ = 0;
    bool             hasExplicitMeasurements_ = false;

    // Build internal op list from OpenQASM (small subset)
    int buildOpsFromOpenQASM(std::string_view qasm, LaunchStatus& status);

    // Small helpers
    static std::string trimCopy(const std::string& s);
};

#endif // ENABLE_CUDAQ
