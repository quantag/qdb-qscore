
#include "BaseQVM.h"

#include "../Log.h"
#include "../Utils.h"
#include "../ConfigLoader.h"

#include "../QiskitProcessor.h"
#include "../TketProcessor.h"
#include "../WebFrontend.h"
#include "../ws/WSServer.h"



void BaseQVM::updateProcessor(PythonFramework framework) {
	if (this->processor != NULL) {
		if (this->processor->getFramework() == framework)
			return;

		delete processor;
	}

	switch (framework) {
	case eQiskit:
	case eGeneric:
		this->processor = new QiskitProcessor();
		break;
	case eTket:
		this->processor = new TketProcessor();
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