#pragma once

#include "BaseQVM.h"

#ifdef ENABLE_CUDAQ


#include <optional>

class CudaQVM : public BaseQVM {
public:
    CudaQVM();
    CudaQVM(ConfigLoader* cfg);
    ~CudaQVM();

    // Required overrides from IQVM
    int loadSourceCode(const std::string& code,
        const std::string& path,
        LaunchStatus& status) override;

    int run(const std::string& in,
        const std::string& out,
        LaunchStatus& status) override;

    int debug(const std::string& in,
        const std::string& out,
        LaunchStatus& status) override;

    std::string getQVMName() override;
    int getSourceLines() override;
    double stepForward() override;

private:
    std::optional<std::string> cudaqSource_;
    std::string translateQasmToCudaq(const std::string &qasm);
};

#endif // ENABLE_CUDAQ
