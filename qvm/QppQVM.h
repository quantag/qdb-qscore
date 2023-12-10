
#pragma once

#include "../interfaces/iqvm.h"
#include "qpp.h"

using namespace qpp;

class WSServer;

class QppQVM : public IQVM {
public:
	QppQVM(WSServer *ws);
	~QppQVM();

	int loadSourceCode(const std::string& fileName);
	int run(const std::string& fileName);
	int debug(const std::string& fileName);

	int getSourceLines();
	void stepForward();

private:
	QCircuit* circuit;
	QEngine* engine;
	WSServer* wsServer;

	QCircuit::iterator mIt; // current state
	std::string sourceCode;
};
