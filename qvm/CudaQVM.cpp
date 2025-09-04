#include "CudaQVM.h"


#ifdef ENABLE_CUDAQ

#include <cudaq.h>
#include "../Log.h"

CudaQVM::CudaQVM() {
    cudaqSource_.reset();
}

CudaQVM::CudaQVM(ConfigLoader* cfg){
//    this->frontend = new WebFrontend();
    cudaqSource_.reset();
    this->sourceCodeParsed = 0;
//    processor = new QiskitProcessor();
    this->cfg = cfg;
}

CudaQVM::~CudaQVM() {

}

int CudaQVM::loadSourceCode(const std::string& code,
    const std::string& path,
    LaunchStatus& status) {
    this->sourceCode = code;
    status.codeType = eOpenQASM;

    cudaqSource_ = code;

    LOGI("CudaQVM: loaded source from %s", path.c_str());
    return ERR_OK;
}

int CudaQVM::run(const std::string& in,
    const std::string& out,
    LaunchStatus& status) {
    if (!cudaqSource_) {
        status.errorMessage = "No CUDA-Q source loaded.";
        return ERR_NOFILE;
    }

    LOGI("CudaQVM: run() stub called.");
    return ERR_OK;
}

int CudaQVM::debug(const std::string& in,
    const std::string& out,
    LaunchStatus& status) {
    status.errorMessage = "CudaQVM::debug not implemented.";
    return ERR_OK;
}

std::string CudaQVM::getQVMName() {
    return "CudaQVM";
}

int CudaQVM::getSourceLines() {
    return 0;// static_cast<int>(BaseQVM::getSourceLines().size());
}

double CudaQVM::stepForward() {
    // Stub: no stepping support yet
    return 0.0;
}


#endif // ENABLE_CUDAQ
