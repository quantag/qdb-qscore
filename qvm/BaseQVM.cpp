
#include "BaseQVM.h"

#include "../Log.h"
#include "../Utils.h"
#include "../ConfigLoader.h"

#include "../processors/QiskitProcessor.h"
#include "../processors/TketProcessor.h"
#include "../processors/CudaQProcessor.h"
#include "../WebFrontend.h"
#include "../ws/WSServer.h"

#include <cctype>
#include <cstring>
#include <filesystem>
#include <sstream>
#include <nlohmann/json.hpp>
namespace fs = std::filesystem;

void BaseQVM::updateProcessor(CodeFramework framework) {
	if (this->processor != NULL) {
		if (this->processor->getFramework() == framework)
			return;

		delete this->processor;
        this->processor = NULL;
	}

	switch (framework) {
	    case eQiskit:
	    case eGeneric:
		    this->processor = new QiskitProcessor(cfg);
		    break;
	    case eTket:
		    this->processor = new TketProcessor(cfg);
		    break;
	    case eCUDAQ:
		    this->processor = new CudaQProcessor(cfg);
		    break;
	    }
}

static int countPhysicalLines(const std::string& text) {
	if (text.empty()) return 0;
	int n = 1;
	for (char c : text) {
		if (c == '\n') n++;
	}
	return n;
}

int BaseQVM::getSourceLines() {
	if (!gateSourceLines.empty()) {
		// C++: real line numbers are reported, so count every line of the file
		return countPhysicalLines(this->sourceCode);
	}
	return Utils::calcNumberOfLines(this->sourceCode);
}

void BaseQVM::setWSSession(WSSession* ws) {
	LOGI("setWSSession");

	if (this->frontend)
		this->frontend->setWSSession(ws);
}

int BaseQVM::prepareSource( const std::string& fileName,
                            const std::string& sessionId,
                            LaunchStatus& status,
                            std::string& preparedSource) {
    int ret = ERR_OK;
    status.pythonFramework = eUnknownFramework;
    status.codeType = eUnknown;

    this->sourceCodeParsed = 0;
    this->sourceCodePerLines.clear();
    this->gateSourceLines.clear();

    std::string file = fileName;
    std::string sourceFolder = cfg ? cfg->getSourceFolder() : SOURCE_FOLDER_DEFAULT;

    if (cfg) {
        sourceFolder = cfg->getSourceFolder();
    }  else {
        LOGE("cfg is null in BaseQVM");
    }

    if (!Utils::fileExists(file)) {
        std::string defaultFolder = sourceFolder + "default";
        std::string serverFile = Utils::findServerFile(defaultFolder, file);
        if (!Utils::fileExists(serverFile)) {
            std::string sessionFolder = sourceFolder + sessionId;
            serverFile = Utils::findServerFile(sessionFolder, file);
        }

        if (!Utils::fileExists(serverFile)) {
            file = cfg ? cfg->getDemoFile() : DEMO_FILE_DEFAULT;

            LOGI("File [%s] not found, using demo file [%s].", serverFile.c_str(), file.c_str());
            ret = ERR_DEMOFILE;
            status.serverFileFound = 0;
        }
        else {
            file = serverFile;
            status.serverFileFound = 1;
        }
    }

    if (!Utils::fileExists(file)) {
        LOGE("File '%s' still not found.", file.c_str());
        return ERR_NOFILE;
    }

    sourceCode = Utils::loadFile(file);
    originalSourceCode = sourceCode;

    status.codeType = Utils::detectCodeType(sourceCode);
    Utils::parseCode(sourceCode, originalParsedCode, status.codeType);

    if (status.codeType == CodeType::ePython) {
        status.pythonFramework = Utils::detectPythonFramework(sourceCode);
        updateProcessor(status.pythonFramework);
        ScriptExecResult result = processor->parsePythonToOpenQASM(sourceCode, sessionId, this->venv);
        if (result.status != 0) {
            status.errorMessage = Utils::getPlainTextFromHTML(result.err);
            return ERR_PARSEERROR;
        }
        preparedSource = result.res;
        if (!takePythonSourceLines(preparedSource)) {
            LOGI("Python processor reported no source lines; stepping line by line (lines may not match the gates)");
        }
    }
    else if (status.codeType == CodeType::eCpp) {
        int cppRet = translateCppSource(file, status, preparedSource);
        if (cppRet != ERR_OK) {
            return cppRet;
        }
    }
    else {
        preparedSource = sourceCode;
    }
    generateCodeMapping(preparedSource, status.codeType);
    logCodeMapping();
    return ret;
}

std::string BaseQVM::getProjectVenv(const std::string& fileName) {
    if (!cfg) return std::string();

    std::string venvRoot = cfg->getVenvRoot();
    std::string projectsRoot = cfg->getProjectsRoot();
    if (venvRoot.empty() || projectsRoot.empty()) return std::string();

    try {
        fs::path file = fs::weakly_canonical(fs::absolute(fileName));
        fs::path root = fs::weakly_canonical(fs::absolute(projectsRoot));

        fs::path rel = file.lexically_relative(root);
        if (rel.empty() || rel.begin() == rel.end()) return std::string();

        std::string project = rel.begin()->string();
        if (project.empty() || project == "." || project == "..") return std::string();

        fs::path venv = fs::path(venvRoot) / project;
        if (fs::exists(venv / "bin" / "python")) {
            return venv.string();
        }
    }
    catch (...) {
        LOGI("getProjectVenv: exception for file: %s", fileName.c_str());
    }
    return std::string();
}

std::string BaseQVM::getVenvIfPresent(const std::string& fileName) {
    try {
        fs::path current = fs::absolute(fileName).parent_path();

        if (current.empty()) {
            LOGI("getVenvIfPresent: no parent directory for file: %s", fileName.c_str());
            return std::string();
        }

        for (; !current.empty(); current = current.parent_path()) {
            fs::path venvPath = current / ".venv";

            if (fs::exists(venvPath) && fs::is_directory(venvPath)) {
                std::string venvStr = venvPath.string();
                LOGI("getVenvIfPresent: detected venv folder: %s", venvStr.c_str());
                return venvStr;
            }

            // Stop when we reach a root (parent is the same as current)
            fs::path parent = current.parent_path();
            if (parent.empty() || parent == current) {
                break;
            }
        }

        // Studio workspaces keep venvs outside the project:
        // <projects.root>/<uid>/... -> <venv.root>/<uid>
        std::string projectVenv = getProjectVenv(fileName);
        if (!projectVenv.empty()) {
            LOGI("getVenvIfPresent: detected project venv: %s", projectVenv.c_str());
            return projectVenv;
        }

        LOGI("getVenvIfPresent: no venv folder found for file: %s", fileName.c_str());
        return std::string();
    }
    catch (...) {
        LOGI(
            "getVenvIfPresent: exception while searching venv for file: %s",
            fileName.c_str()
        );
        return std::string();
    }
}

// true if line starts with word followed by a non-identifier character or the end
// ("gate" matches "gate foo ..." but not the custom gate call "gate_W q[0];")
static bool startsWithWord(const std::string& line, const char* word) {
    size_t n = std::strlen(word);
    if (line.compare(0, n, word) != 0)
        return false;
    if (line.size() == n)
        return true;
    char c = line[n];
    return !(std::isalnum(static_cast<unsigned char>(c)) || c == '_');
}

// Return true if this QASM line corresponds to an operation that
// actually changes or uses the QVM state (gate, measure, reset, etc.).
bool BaseQVM::isExecutableQasmLine(const std::string& rawLine) {
    std::string line = rawLine;
    Utils::trim(line);
    if (line.empty())
        return false;

    // Comments
    if (line[0] == '/' || line[0] == '#')
        return false;

    // Declarations and includes
    if (startsWithWord(line, "OPENQASM"))
        return false;
    if (startsWithWord(line, "include"))
        return false;
    if (startsWithWord(line, "qreg"))
        return false;
    if (startsWithWord(line, "creg"))
        return false;
    if (startsWithWord(line, "gate"))
        return false;
    if (startsWithWord(line, "opaque"))
        return false;
    if (line == "{" || line == "}")
        return false;
    if (startsWithWord(line, "barrier"))
        return false;

    // Everything else we treat as executable for now:
    // - standard gates: h, x, y, z, rx, ry, rz, u, u3, cx, cz, swap, etc.
    // - measure, reset, conditional ops like "if (c==1) x q[0];"
    return true;
}

void BaseQVM::generateCodeMapping(const std::string& preparedSource,
    CodeType codeType) {
 
    switch (codeType) {
        case CodeType::ePython: {
                if (!gateSourceLines.empty())
                    generateInstructionLineMapping();
                else
                    generatePythonCodeMapping(preparedSource);
                break;
        }
        case CodeType::eOpenQASM: {
                generateOpenQASMCodeMapping(preparedSource);
                break;
            }
        case CodeType::eCpp: {
                generateInstructionLineMapping();
                break;
            }
        default:
            LOGE("Not supported source type: %d", codeType);
    }

}

void BaseQVM::logCodeMapping() const {
    LOGI("==== Code mapping: original source line -> QASM instruction indices ====");

    if (sourceToQasmLines.empty()) {
        LOGI("  (mapping is empty)");
        return;
    }

    for (std::size_t srcIdx = 0; srcIdx < sourceToQasmLines.size(); ++srcIdx) {
        const auto& instrList = sourceToQasmLines[srcIdx];

        std::string listStr = "[";
        for (std::size_t j = 0; j < instrList.size(); ++j) {
            // Now we treat values as 0-based instruction indices, no +1
            listStr += std::to_string(instrList[j]);
            if (j + 1 < instrList.size()) {
                listStr += ", ";
            }
        }
        listStr += "]";

        int srcLineOneBased = static_cast<int>(srcIdx) + 1;
        LOGI("  src %d -> %s", srcLineOneBased, listStr.c_str());
    }

    LOGI("==== End of code mapping ====");
}


void BaseQVM::generateOpenQASMCodeMapping(const std::string& preparedSource) {
    std::vector<std::string> originalLines;
    std::vector<std::string> qasmLines;

    int originalCount = Utils::parseSourcePerLines(originalSourceCode, originalLines);
    int qasmCount = Utils::parseSourcePerLines(preparedSource, qasmLines);

    if (originalCount <= 0 || qasmCount <= 0) {
        LOGI("BaseQVM::generateOpenQASMCodeMapping] no lines to map");
        return;
    }

    sourceToQasmLines.assign(originalCount, {});

    int n = std::min(originalCount, qasmCount);
    int execIndex = 0; // 0-based "gate number" in the circuit

    for (int i = 0; i < n; ++i) {
        if (isExecutableQasmLine(qasmLines[i])) {
            // Map original line i (0-based) to gate execIndex
            sourceToQasmLines[i].push_back(execIndex);
            ++execIndex;
        }
        // Non-executable lines remain mapped to []
    }

    LOGI("BaseQVM::generateOpenQASMCodeMapping] mapped %d executable QASM lines", execIndex);
}

static std::string shellQuote(const std::string& s) {
#ifdef _WIN32
    return "\"" + s + "\"";
#else
    std::string r = "'";
    for (char c : s) {
        if (c == '\'') r += "'\\''";
        else r += c;
    }
    return r + "'";
#endif
}

int BaseQVM::translateCppSource(const std::string& file, LaunchStatus& status, std::string& preparedSource) {
    std::string tool = cfg ? cfg->getCppQasmTool() : CPP_QASM_TOOL_DEFAULT;
    std::string cmd = shellQuote(tool) + " " + shellQuote(file);
    LOGI("CUDA-Q C++ source, running [%s]", cmd.c_str());

    CommandResult res;
    try {
        res = Utils::exec2(cmd);
    }
    catch (const std::exception& e) {
        status.errorMessage = std::string("Cannot run C++ translator: ") + e.what();
        return ERR_PARSEERROR;
    }

    nlohmann::json j;
    try {
        j = nlohmann::json::parse(res.output);
    }
    catch (...) {
        status.errorMessage = "C++ translator (" + tool + ") failed: " + res.output.substr(0, 500);
        return ERR_PARSEERROR;
    }
    if (j.value("status", 1) != 0) {
        status.errorMessage = j.value("error", std::string("C++ translation failed"));
        LOGE("C++ translation failed: %s", status.errorMessage.c_str());
        return ERR_PARSEERROR;
    }

    preparedSource = j.value("qasm", std::string());
    std::vector<int> lines = j.value("lines", std::vector<int>());

    setGateSourceLines(preparedSource, lines);
    LOGI("CUDA-Q C++ kernel [%s]: %zu instructions",
        j.value("kernel", std::string("?")).c_str(), gateSourceLines.size());
    return ERR_OK;
}

// qasmLineSources has the source line of every line of qasm (0 for declarations);
// keeps the ones of executable instructions, in circuit order.
void BaseQVM::setGateSourceLines(const std::string& qasm, const std::vector<int>& qasmLineSources) {
    gateSourceLines.clear();
    std::istringstream in(qasm);
    std::string line;
    size_t i = 0;
    while (std::getline(in, line)) {
        if (!line.empty() && line.back() == '\r') {
            line.pop_back();
        }
        if (isExecutableQasmLine(line)) {
            gateSourceLines.push_back(i < qasmLineSources.size() ? qasmLineSources[i] : 0);
        }
        i++;
    }
}

// Python (Qiskit): the processor appends "// qscore-lines: l1,l2,..." to the QASM with
// the program line of every QASM line. Removes that line from preparedSource and fills
// gateSourceLines. Returns false when the line is missing or unusable.
bool BaseQVM::takePythonSourceLines(std::string& preparedSource) {
    size_t pos = preparedSource.rfind(QASM_LINES_MARKER);
    if (pos == std::string::npos || (pos > 0 && preparedSource[pos - 1] != '\n')) {
        return false;
    }
    size_t end = preparedSource.find('\n', pos);
    std::string list = preparedSource.substr(pos + std::strlen(QASM_LINES_MARKER),
        end == std::string::npos ? std::string::npos : end - pos - std::strlen(QASM_LINES_MARKER));
    preparedSource.erase(pos, end == std::string::npos ? std::string::npos : end - pos + 1);

    std::vector<int> lines;
    std::istringstream items(list);
    std::string item;
    while (std::getline(items, item, ',')) {
        try {
            lines.push_back(std::stoi(item));
        }
        catch (...) {
            LOGE("Bad source line list from the Python processor: [%s]", list.c_str());
            return false;
        }
    }

    setGateSourceLines(preparedSource, lines);
    bool any = false;
    for (int l : gateSourceLines) {
        if (l > 0) { any = true; break; }
    }
    if (!any) {
        gateSourceLines.clear();
        return false;
    }
    LOGI("Python: %zu instructions with source lines", gateSourceLines.size());
    return true;
}

// gateSourceLines -> sourceToQasmLines (source line -> instruction indices)
void BaseQVM::generateInstructionLineMapping() {
    int n = countPhysicalLines(originalSourceCode);
    sourceToQasmLines.assign(n, {});
    for (size_t i = 0; i < gateSourceLines.size(); i++) {
        int l = gateSourceLines[i];
        if (l >= 1 && l <= n) {
            sourceToQasmLines[l - 1].push_back(static_cast<int>(i));
        }
    }
}

// Detect if a line of Python source is a pure comment (or comment after whitespace)
bool BaseQVM::isPythonCommentLine(const std::string& rawLine) {
    std::string line = rawLine;
    Utils::trim(line);
    if (line.empty()) {
        return false; // treat empty as "no-op" but not specifically a comment
    }
    // Python comment: line starts with '#'
    return !line.empty() && line[0] == '#';
}


void BaseQVM::generatePythonCodeMapping(const std::string& preparedSource) {
    // Split original (Python) source into lines
    std::vector<std::string> originalLines;
    int originalCount = Utils::parseSourcePerLines(originalSourceCode, originalLines);

    // Split prepared (generated OpenQASM) source into lines
    std::vector<std::string> qasmLines;
    int qasmCount = Utils::parseSourcePerLines(preparedSource, qasmLines);

    if (originalCount <= 0) {
        LOGI("BaseQVM::generatePythonCodeMapping] no original lines");
        sourceToQasmLines.clear();
        return;
    }

    sourceToQasmLines.assign(originalCount, {});

    int n = std::min(originalCount, qasmCount);

    bool inDocstring = false;
    std::string docToken; // """ or '''

    for (int i = 0; i < n; ++i) {
        std::string line = originalLines[i];
        std::string trimmed = line;
        Utils::trim(trimmed);

        // 1) Pure comment line -> no-op
        if (isPythonCommentLine(line)) {
            LOGI("BaseQVM::generatePythonCodeMapping] Python comment at src line %d, mapping []", i + 1);
            continue;
        }

        // 2) Docstring handling (very simple but good enough for Qiskit examples)
        if (!inDocstring) {
            // Look for opening """ or '''
            if (trimmed.rfind("\"\"\"", 0) == 0 || trimmed.rfind("'''", 0) == 0) {
                docToken = trimmed.substr(0, 3);
                inDocstring = true;
                LOGI("BaseQVM::generatePythonCodeMapping] Docstring start at src line %d", i + 1);

                // Single-line docstring: """ text """
                std::size_t secondPos = trimmed.find(docToken, 3);
                if (secondPos != std::string::npos) {
                    // Starts and ends on same line
                    inDocstring = false;
                    LOGI("BaseQVM::generatePythonCodeMapping] Docstring end (same line) at src line %d", i + 1);
                }

                // In any case, treat this line as non-op
                continue;
            }
        }
        else {
            // We are inside a docstring block
            LOGI("BaseQVM::generatePythonCodeMapping] Inside docstring at src line %d", i + 1);

            // Check for closing token
            if (trimmed.find(docToken) != std::string::npos) {
                inDocstring = false;
                LOGI("BaseQVM::generatePythonCodeMapping] Docstring end at src line %d", i + 1);
            }

            // Entire docstring block is treated as non-op
            continue;
        }

        // 3) Normal (non-comment, non-docstring) line:
        //    temporary 1:1 mapping: src line i -> prepared line i
        sourceToQasmLines[i].push_back(i);
    }

    LOGI("BaseQVM::generatePythonCodeMapping] temporary 1:1 mapping (excluding comments/docstrings), lines=%d", n);
}
