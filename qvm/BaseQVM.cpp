
#include "BaseQVM.h"

#include "../Log.h"
#include "../Utils.h"
#include "../ConfigLoader.h"

#include "../processors/QiskitProcessor.h"
#include "../processors/TketProcessor.h"
#include "../processors/CudaQProcessor.h"
#include "../WebFrontend.h"
#include "../ws/WSServer.h"

#include <filesystem>
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
	    }
}

int BaseQVM::getSourceLines() {
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
    }
    else {
        preparedSource = sourceCode;
    }

    return ret;
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

