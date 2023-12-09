
#pragma once

#include "../interfaces/iqvm.h"
#include "qpp.h"

using namespace qpp;

class WSServer;

class QppQVM : public IQVM {
public:
	QppQVM(WSServer *ws);
	~QppQVM();

	virtual int loadSourceCode(const std::string& fileName);

	virtual int run(const std::string& fileName);
	virtual int debug(const std::string& fileName);

private:
	QCircuit* circuit;
	QEngine* engine;
	WSServer* wsServer;
};
