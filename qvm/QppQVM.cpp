
#include "QppQVM.h"


#include "../Log.h"
#include "../ws/WSServer.h"
#include "../Utils.h"

#define DEMO_FILE "/home/qbit/qasm/file1.qasm"

QppQVM::QppQVM(WSServer* ws) : circuit(NULL), engine(NULL) {
	this->wsServer = ws;
}

QppQVM::~QppQVM() {
	SAFE_DELETE(circuit);
	SAFE_DELETE(engine);
}

int QppQVM::loadSourceCode(const std::string& fileName) {
	LOGI("[%s]", fileName.c_str());
	int ret = 0;
	SAFE_DELETE(circuit);

	sourceCode = "";
	std::string file = fileName;

	if (!Utils::fileExists(file)) {
		LOGI("File [%s] not exist, use demo file [%s]", fileName.c_str(), DEMO_FILE);
		file = DEMO_FILE;
		ret = 1;
	}

	if (!Utils::fileExists(file) ) {
		LOGI("File '%s' not exists", file.c_str());
		return 1;
	}
	else {
		LOGI("File '%s' exist !", file.c_str());
	}
	sourceCode = Utils::loadFile(file);
	LOGI("Loaded %u bytes from [%s]", sourceCode.size(), file.c_str());

	std::string encodedSourceCode = Utils::encode64(sourceCode);
	circuit = qasm::readFromFile(file);
	
	std::string data = "{\"command\":\"load\",\"code\":\"" + encodedSourceCode + "\"}";
	int ret1 = wsServer->send(data);
	LOGI("WS SEND ret %d", ret1);

	return ret;
}


int QppQVM::run(const std::string& fileName) {
	LOGI("%s", fileName.c_str());

	ASSERT(loadSourceCode(fileName));
	LOGI("Loaded source code from [%s]", fileName.c_str());

	SAFE_DELETE(engine);
	engine = QEngine::instance(*circuit); // create an engine out of a quantum circuit

	engine->execute();
	return 0;
}

int QppQVM::debug(const std::string& fileName) {
	LOGI("%s", fileName.c_str());

	int ret = loadSourceCode(fileName);
	if (ret != 0) {
		LOGE("Error loading sources from [%s]", fileName.c_str());
		return ret;
	}
	LOGI("Loaded source code from [%s]", fileName.c_str());

	SAFE_DELETE(engine);
	engine = QEngine::instance(*circuit); // create an engine out of a quantum circuit

	mIt = circuit->cbegin();
	return 0;
}

int QppQVM::getSourceLines() {
	return Utils::calcNumberOfLines(this->sourceCode);
}

// Execute next line
void QppQVM::stepForward() {
	LOGI("");

	if (mIt != circuit->end()) {
		LOGI("Excuting next line..");
		engine->execute(mIt);

		qpp::ket psi = engine->get_psi();
		cmat rho = prj(psi);
		//	sendUpdateState();

		mIt++;
	}
	else {
		LOGI("Reached and of circuit..");
	}


}