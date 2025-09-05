#include "CudaQVM.h"


#ifdef ENABLE_CUDAQ
#include <fstream>
#include <sstream>
#include <nlohmann/json.hpp>
#include <cudaq.h>
#include "../Log.h"
#include "../Utils.h"
#include "../RestClient.h"
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
    this->originalSourceCode = code;
    this->cudaqSource_ = code;
    this->sourceCodeParsed = 1;
    status.codeType = eOpenQASM;

    LOGI("CudaQVM: loaded QASM source from [%s], %d lines.",
         path.c_str(),
         Utils::calcNumberOfLines(code));
    return ERR_OK;
}


int CudaQVM::run(const std::string& code,
                 const std::string& path,
                 LaunchStatus& status) {
    // Step 1: Load QASM source
    std::string qasmSource;
    if (Utils::fileExists(code)) {
        qasmSource = Utils::loadFile(code);
        if (qasmSource.empty()) {
            status.errorMessage = "Failed to read QASM file: " + code;
            return ERR_NOFILE;
        }
    } else {
        qasmSource = code;
    }

    int ret = loadSourceCode(qasmSource, path, status);
    if (ret != ERR_OK && ret != ERR_DEMOFILE)
        return ret;

    if (!cudaqSource_) {
        status.errorMessage = "No CUDA-Q source loaded.";
        return ERR_NOFILE;
    }

    try {
        // Step 2: Send QASM to Flask microservice
        std::string url = "http://127.0.0.1:5005/run";  // or your production URL
        nlohmann::json payload;
        payload["qasm"] = qasmSource;
        payload["shots"] = 1000;

        RestClient client("http://127.0.0.1:5005/run");
        std::string response = client.doPost(payload.dump());
        auto jsonResp = nlohmann::json::parse(response);
        if (jsonResp.contains("error")) {
            status.errorMessage = jsonResp["error"];
            LOGE("CudaQVM error: %s", status.errorMessage.c_str());
            return ERR_RUNERROR;
        }

        if (jsonResp.contains("result")) {
            //LOGI("CudaQVM run result: %s", jsonResp["result"].dump().c_str());
        }
    }
    catch (std::exception& e) {
        status.errorMessage = e.what();
        LOGE("CudaQVM exception: %s", e.what());
        return ERR_RUNERROR;
    }

    return ERR_OK;
}

int CudaQVM::debug(const std::string& in,
    const std::string& out,
    LaunchStatus& status) {
    status.errorMessage = "CudaQVM::debug not implemented.";
    return ERR_OK;
}

std::string CudaQVM::getQVMName() {
    return "CudaQVM 0.2";
}

int CudaQVM::getSourceLines() {
    return 0;// static_cast<int>(BaseQVM::getSourceLines().size());
}

double CudaQVM::stepForward() {
    // Stub: no stepping support yet
    return 0.0;
}

std::string CudaQVM::translateQasmToCudaq(const std::string &qasm) {
    std::stringstream ss;
    ss << "#include <cudaq.h>\n";
    ss << "#include <iostream>\n\n";

    // Kernel
    ss << "__qpu__ void circuit() {\n";

    std::istringstream lines(qasm);
    std::string line;
    while (std::getline(lines, line)) {
        Utils::trim(line);
        if (line.empty() || line[0] == '/' ||
            line.rfind("OPENQASM", 0) == 0 ||
            line.rfind("include", 0) == 0)
            continue;

        if (line.rfind("qreg", 0) == 0) {
            // Example: qreg q[2];
            auto l = line.find('[');
            auto r = line.find(']');
            int n = std::stoi(line.substr(l + 1, r - l - 1));
            ss << "  auto q = cudaq::qvector(" << n << ");\n";
        } else if (line.rfind("h ", 0) == 0) {
            int idx = Utils::extractIndex(line);
            ss << "  h(q[" << idx << "]);\n";
        } else if (line.rfind("x ", 0) == 0) {
            int idx = Utils::extractIndex(line);
            ss << "  x(q[" << idx << "]);\n";
        } else if (line.rfind("rz", 0) == 0) {
            // Example: rz(3.14) q[0];
            auto l = line.find('(');
            auto r = line.find(')');
            std::string angle = line.substr(l + 1, r - l - 1);
            int idx = Utils::extractIndex(line);
            ss << "  rz(" << angle << ", q[" << idx << "]);\n";
        } else if (line.rfind("cx", 0) == 0) {
            // Example: cx q[0], q[1];
            auto l = line.find('[');
            auto c1 = std::stoi(line.substr(l + 1, line.find(']', l) - l - 1));
            l = line.find('[', l + 1);
            auto c2 = std::stoi(line.substr(l + 1, line.find(']', l) - l - 1));
            ss << "  cx(q[" << c1 << "], q[" << c2 << "]);\n";
        } else if (line.rfind("measure", 0) == 0) {
            // ignore in kernel, handled in main() via cudaq::sample
        }
    }

    ss << "}\n\n";

    // Main function
    ss << "int main() {\n";
    ss << "  auto counts = cudaq::sample(circuit);\n";
    ss << "  std::cout << counts << \"\\n\";\n";
    ss << "}\n";

    return ss.str();
}


#endif // ENABLE_CUDAQ
