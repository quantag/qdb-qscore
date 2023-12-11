
#pragma once

#include "../interfaces/iqvm.h"

#include "qpp.h"

using namespace qpp;

class WSServer;
class IFrontend;

class QppQVM : public IQVM {
public:
	QppQVM(WSServer *ws);
	~QppQVM();

	int loadSourceCode(const std::string& fileName);
	int run(const std::string& fileName);
	int debug(const std::string& fileName);

	int getSourceLines();
	void stepForward();

	static std::vector<complexNumber> convertToStdVector(const qpp::ket& eigenVector);
	static matrix2d convertToMatrix2D(const qpp::cmat& eigenMatrix);
//	static std::vector<std::complex<double>> getQubitStateVector(const QEngine& quantumSystem, int qubitIndex);

private:
	QCircuit* circuit;
	QEngine* engine;
	IFrontend* frontend;

	QCircuit::iterator mIt; // current state
	void setCurrentState(const qpp::ket& psi, const qpp::cmat& mat);

};
