
#pragma once

#include "../interfaces/iqvm.h"

#include "qpp.h"

using namespace qpp;

class WSSession;
class IFrontend;
class PythonProcessor;

class QppQVM : public IQVM {
public:
	QppQVM();
	~QppQVM();

	int loadSourceCode(const std::string& fileName, const std::string& sessionId, std::string &errorMessage);
	int run(const std::string& fileName, const std::string& sessionId);
	int debug(const std::string& fileName, const std::string& sessionId);

	int getSourceLines();
	void stepForward();

	void setWSSession(WSSession* wsSession);

	static std::vector<complexNumber> convertToStdVector(const qpp::ket& eigenVector);
	static matrix2d convertToMatrix2D(const qpp::cmat& eigenMatrix);
//	static std::vector<std::complex<double>> getQubitStateVector(const QEngine& quantumSystem, int qubitIndex);
//	static std::string parsePythonToOpenQASM(const std::string& sourceCode);
	void updateProcessor(PythonFramework framework);

private:
	//QCircuit* circuit;
	// Smart pointer to store QCircuit object
	std::unique_ptr<QCircuit> circuit;

	QEngine* engine;
	IFrontend* frontend;

	QCircuit::iterator mIt; // current state
	void setCurrentState(const qpp::ket& psi);

	PythonProcessor* processor;
};
