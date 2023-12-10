
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

	std::string src = "";
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
	src = Utils::loadFile(file);
	LOGI("Loaded %u bytes from [%s]", src.size(), file.c_str());

	src = Utils::encode64(src);
	circuit = qasm::readFromFile(file);
	
	std::string data = "{\"command\":\"load\",\"code\":\"" + src + "\"}";
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
	engine->execute(mIt);

	qpp::ket psi = engine->get_psi();
	cmat rho = prj(psi);

	return 0;
}