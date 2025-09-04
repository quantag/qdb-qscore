#include "CudaQVM.h"

#ifdef ENABLE_CUDAQ

#include "../Log.h"
#include "../Utils.h"
#include "../WebFrontend.h"
#include "../ConfigLoader.h"

#include <sstream>
#include <fstream>
#include <stdexcept>

// -------------------- ctor/dtor --------------------
CudaQVM::CudaQVM() {
    this->frontend = new WebFrontend();
    this->sourceCodeParsed = 0;
    this->nQubits = 0;
    this->cfg = nullptr;
}

CudaQVM::CudaQVM(ConfigLoader* cfg) : CudaQVM() {
    this->cfg = cfg;
}

CudaQVM::~CudaQVM() {
    SAFE_DELETE(frontend);
}

// -------------------- loadSourceCode (OpenQASM only) --------------------
int CudaQVM::loadSourceCode(const std::string& fileName,
    const std::string& sessionId,
    LaunchStatus& status) {
    LOGI("[CudaQVM] loadSourceCode file='%s' session='%s'",
        fileName.c_str(), sessionId.c_str());

    int ret = ERR_OK;
    status.pythonFramework = eUnknownFramework;
    status.codeType = eUnknown;
    status.errorMessage.clear();

    // Reset BaseQVM bookkeeping
    this->sourceCodeParsed = 0;
    this->sourceCode.clear();
    this->originalSourceCode.clear();
    this->sourceCodePerLines.clear();
    this->originalParsedCode.clear();
    this->nQubits = 0;

    // Resolve file (mirror QppQVM logic)
    std::string file = fileName;
    std::string sourceFolder = SOURCE_FOLDER;
    if (cfg) sourceFolder = cfg->getSourceFolder();

    if (!Utils::fileExists(file)) {
        // try server default
        std::string defaultFolder = sourceFolder + std::string("default");
        std::string serverFile = Utils::findServerFile(defaultFolder, file);
        if (!Utils::fileExists(serverFile)) {
            // try session folder
            std::string sessionFolder = sourceFolder + sessionId;
            serverFile = Utils::findServerFile(sessionFolder, file);
        }

        if (!Utils::fileExists(serverFile)) {
            LOGI("Server file not found, falling back to demo");
            if (cfg) file = cfg->getDemoFile(); else file = DEMO_FILE;
            ret = ERR_DEMOFILE;
            status.serverFileFound = 0;
        }
        else {
            file = serverFile;
            status.serverFileFound = 1;
        }
    }

    if (!Utils::fileExists(file)) {
        status.errorMessage = "File not found: " + file;
        LOGE("%s", status.errorMessage.c_str());
        return ERR_NOFILE;
    }

    // Load source
    this->sourceCode = Utils::loadFile(file);
    this->originalSourceCode = this->sourceCode;
    LOGI("Loaded %u bytes from '%s'", (unsigned)sourceCode.size(), file.c_str());

    // Detect code type: we only support OpenQASM here
    status.codeType = Utils::detectCodeType(this->sourceCode);
    if (status.codeType != CodeType::eOpenQASM) {
        status.errorMessage = "CUDA-Q backend supports OpenQASM only at this step.";
        LOGE("%s", status.errorMessage.c_str());
        return ERR_PARSEERROR;
    }

    // Parse per-line meta and choose first executable line for UI caret
    Utils::parseCode(this->sourceCode, this->originalParsedCode, status.codeType);
    Utils::parseSourcePerLines(this->sourceCode, this->sourceCodePerLines);
    this->currentState.currentLine = Utils::getFirstLine(this->originalParsedCode, 2) + 1;

    // Send code to frontend
    if (frontend) {
        int fr = frontend->loadCode(this->sourceCode);
        LOGI("frontend.loadCode -> %d", fr);
    }

    // Build CUDA-Q internal operations from OpenQASM (subset)
    int brc = buildOpsFromOpenQASM(this->sourceCode, status);
    if (brc != ERR_OK) {
        LOGE("OpenQASM -> CUDA-Q ops parse error: %s", status.errorMessage.c_str());
        return brc;
    }

    // Commit derived info to BaseQVM
    this->nQubits = static_cast<int>(numQubits_);
    this->sourceCodeParsed = 1;

    return ret;
}

// -------------------- OpenQASM -> ops_ (subset) --------------------
int CudaQVM::buildOpsFromOpenQASM(std::string_view qasm, LaunchStatus& status) {
    ops_.clear();
    hasExplicitMeasurements_ = false;
    numQubits_ = 0;

    std::unordered_map<std::string, std::size_t> qindex; // "q[3]" -> 3

    auto parseIndex = [](const std::string& token) -> std::pair<std::string, std::size_t> {
        auto lb = token.find('[');
        auto rb = token.find(']');
        if (lb == std::string::npos || rb == std::string::npos || rb <= lb + 1)
            throw std::runtime_error("Bad qubit token: " + token);
        auto name = token.substr(0, lb);
        auto idx = static_cast<std::size_t>(std::stoul(token.substr(lb + 1, rb - lb - 1)));
        return { name, idx };
        };

    std::istringstream iss{ std::string(qasm) };
    std::string line;
    std::size_t lineNo = 0;

    std::regex reReg(R"(^\s*(qreg|creg)\s+([A-Za-z_]\w*)\s*\[\s*(\d+)\s*\]\s*;.*$)");
    std::regex reUnary(R"(^\s*(h|x|y|z|s|t)\s+([A-Za-z_]\w*\[\d+\])\s*;.*$)");
    std::regex reRot(R"(^\s*(rx|ry|rz)\s*\(\s*([^\)]+)\s*\)\s+([A-Za-z_]\w*\[\d+\])\s*;.*$)");
    std::regex reCnot(R"(^\s*(cx|cnot)\s+([A-Za-z_]\w*\[\d+\])\s*,\s*([A-Za-z_]\w*\[\d+\])\s*;.*$)");
    std::regex reMeas(R"(^\s*measure\s+([A-Za-z_]\w*\[\d+\])\s*->\s*([A-Za-z_]\w*\[\d+\])\s*;.*$)");
    std::regex reBarrier(R"(^\s*barrier\b.*$)");
    std::regex reComment(R"(^\s*//.*$)");

    while (std::getline(iss, line)) {
        ++lineNo;
        std::smatch m;
        std::string L = line;
        Utils::trim(L);
        if (L.empty() || std::regex_match(L, m, reComment)) continue;

        if (std::regex_match(L, m, reReg)) {
            std::string kind = m[1];
            std::string name = m[2];
            std::size_t size = static_cast<std::size_t>(std::stoul(m[3]));
            if (kind == "qreg") {
                for (std::size_t i = 0; i < size; ++i)
                    qindex[name + "[" + std::to_string(i) + "]"] = i;
                numQubits_ = std::max(numQubits_, size);
            }
            continue;
        }

        if (std::regex_match(L, m, reBarrier)) continue;

        if (std::regex_match(L, m, reUnary)) {
            std::string gate = m[1];
            auto [nm, idx] = parseIndex(m[2]);
            ops_.push_back([gate, idx](cudaq::kernel_builder<>& k,
                std::vector<cudaq::QuakeValue>& q) {
                    if (gate == "h") k.h(q[idx]);
                    else if (gate == "x") k.x(q[idx]);
                    else if (gate == "y") k.y(q[idx]);
                    else if (gate == "z") k.z(q[idx]);
                    else if (gate == "s") k.s(q[idx]);
                    else if (gate == "t") k.t(q[idx]);
                });
            continue;
        }

        if (std::regex_match(L, m, reRot)) {
            std::string gate = m[1];
            double theta = std::stod(std::string(m[2]));
            auto [nm, idx] = parseIndex(m[3]);
            ops_.push_back([gate, theta, idx](cudaq::kernel_builder<>& k,
                std::vector<cudaq::QuakeValue>& q) {
                    if (gate == "rx") k.rx(theta, q[idx]);
                    else if (gate == "ry") k.ry(theta, q[idx]);
                    else if (gate == "rz") k.rz(theta, q[idx]);
                });
            continue;
        }

        if (std::regex_match(L, m, reCnot)) {
            auto [nm1, c] = parseIndex(m[2]);
            auto [nm2, t] = parseIndex(m[3]);
            ops_.push_back([c, t](cudaq::kernel_builder<>& k,
                std::vector<cudaq::QuakeValue>& q) {
                    std::vector<cudaq::QuakeValue> ctrls;
                    ctrls.push_back(q[c]);
                    k.x<cudaq::ctrl>(q[c], q[t]);   // controlled-X

                });
            continue;
        }


        if (std::regex_match(L, m, reMeas)) {
            hasExplicitMeasurements_ = true;
            continue;
        }

        if (L.rfind("OPENQASM", 0) == 0 || L.rfind("include", 0) == 0) continue;

        status.errorMessage = "Unsupported OpenQASM at line " + std::to_string(lineNo) + ": " + L;
        return ERR_PARSEERROR;
    }

    if (numQubits_ == 0) {
        status.errorMessage = "No qreg declared in OpenQASM.";
        return ERR_PARSEERROR;
    }
    return ERR_OK;
}


// Utils
std::string CudaQVM::trimCopy(const std::string& s) {
    std::string t = s;
    Utils::trim(t);
    return t;
}

#endif // ENABLE_CUDAQ
