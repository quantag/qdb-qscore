
/*
 * Copyright (c) 2024 Quantag IT Solutions GmbH
 *
 * This source code is licensed under the MIT license found in the
 * LICENSE file in the root directory of this source tree.
 */

#include "QppQVM.h"

#include "../Log.h"
#include "../ws/WSServer.h"
#include "../Utils.h"

#include "../WebFrontend.h"
#include "../processors/QiskitProcessor.h"
#include "../processors/TketProcessor.h"
#include "../processors/CudaQProcessor.h"

#include "../ConfigLoader.h"



QppQVM::QppQVM(ConfigLoader* cfg) : engine(nullptr) {
	this->frontend = new WebFrontend();
	this->sourceCodeParsed = 0;
	processor = new QiskitProcessor();
	this->cfg = cfg;
}

QppQVM::~QppQVM() {
	SAFE_DELETE(engine);
	SAFE_DELETE(frontend);
	delete processor;
}


int QppQVM::loadSourceCode(const std::string& fileName,
	const std::string& sessionId,
	LaunchStatus& status) {
	std::string preparedSource;
	int ret = prepareSource(fileName, sessionId, status, preparedSource);
	if (ret != ERR_OK && ret != ERR_DEMOFILE) 
		return ret;

	LOGI("prepared source = [%s]", preparedSource.c_str());

	int nLines = Utils::parseSourcePerLines(preparedSource, this->sourceCodePerLines);
	LOGI("Parsed lines: %d", nLines);

	try {
		std::istringstream iss(preparedSource);
		circuit = std::make_unique<qpp::QCircuit>(qasm::read(iss));
		nQubits = circuit->get_nq();
		sourceCodeParsed = 1;
	}
	catch (const std::exception& e) {
		status.errorMessage = e.what();
		return ERR_PARSEERROR;
	}
	catch (...) {
		status.errorMessage = "QPP parser failed.";
		return ERR_PARSEERROR;
	}
	return ret;
}



int QppQVM::run(const std::string& fileName, const std::string& sessionId, LaunchStatus& status) {
	LOGI("%s sessionId = [%s]", fileName.c_str(), sessionId.c_str());

	ASSERT( loadSourceCode(fileName, sessionId, status) );
	LOGI("Loaded source code from [%s] parsed = %d", fileName.c_str(), this->sourceCodeParsed);

	SAFE_DELETE(engine);
	if (this->circuit && this->sourceCodeParsed) {
		engine = QEngine::instance(*circuit); // create an engine out of a quantum circuit
		engine->execute();
	}
	return ERR_OK;
}

int QppQVM::debug(const std::string& fileName, const std::string& sessionId, LaunchStatus& status) {
	LOGI("%s sessionId = [%s]", fileName.c_str(), sessionId.c_str());

	int ret = loadSourceCode(fileName, sessionId, status);
	LOGI("loadSourceCode ret %d", ret);
	if (ret == ERR_NOFILE) {
		LOGE("Error loading sources from [%s] [%s]", fileName.c_str(), status.errorMessage.c_str());
		return ret;
	}
	LOGI("Loaded source code from [%s] parsed = %d", fileName.c_str(), this->sourceCodeParsed);

	if (!this->sourceCodeParsed) {
		LOGE("Source parse error [%s]", status.errorMessage.c_str());
		ret = ERR_PARSEERROR;
	}

	SAFE_DELETE(engine);
	if(this->circuit && this->sourceCodeParsed) {
		engine = QEngine::instance(*circuit); // create an engine out of a quantum circuit
		mIt = circuit->begin();
		LOGI("Iterator initialized");
	}

	return ret;
}


// Execute next line
double QppQVM::stepForward() {
	LOGI("");

	if (!circuit || !this->sourceCodeParsed) {
		LOGI("Source code not parsed. Simulate. Line = %d", ++this->currentState.currentLine);
		return 0;
	}

	if (mIt != circuit->end()) {
		LOGI("Executing next line.. %d", this->currentState.currentLine);

		//this->currentState.currentLine ++; // if comments, then skip them.. 

	//	Utils::logSourceCode(originalParsedCode);
		LOGI("currentLine before getNextLine = %d", this->currentState.currentLine);
		this->currentState.currentLine = Utils::getNextLine(this->currentState.currentLine - 1, this->originalParsedCode, 2) + 1; // in UI line numbers starts from 1..
		LOGI("currentLine after getNextLine = %d", this->currentState.currentLine);

		this->currentState.code = Utils::encode64( this->sourceCode );

	//	if(this->getSourceLines()>0)
	//		this->currentState.currentLine %= this->getSourceLines();


		try {
			auto start = std::chrono::steady_clock::now();
			engine->execute( mIt++ ); // crash

			qpp::ket psi = engine->get_psi();
//			cmat rho = prj(psi);

			setCurrentState(psi);	
			// const States& st = States::get_instance();  ?

			int ret1 = frontend->updateState(currentState);
			LOGI("frontend.updateState ret %d", ret1);

			auto stop = std::chrono::steady_clock::now();
			// auto duration = std::chrono::duration_cast<std::chrono::microseconds>(stop - start); 
			auto duration = std::chrono::duration<double>(stop - start);
			double timeSec = duration.count();

			LOGI("Execution time: (%f sec)", timeSec);
			return duration.count();
		}
		catch (...) {
			LOGE("Error executing next line");
		}
	}
	else {
		LOGI("Reached end of circuit..");
	}
	return 0;
}

// Convert qpp::ket to std::vector<complexNumber>
std::vector<complexNumber> QppQVM::convertToStdVector(const qpp::ket& eigenVector) {
	std::vector<complexNumber> result;

	int rows = (int)eigenVector.rows();
	int cols = (int)eigenVector.cols();

	for (int i = 0; i < rows; i++) {
		complexNumber cn;
		cn.a = eigenVector(i).real();
		cn.b = eigenVector(i).imag();
		result.push_back(cn);
	}

	return result;
}

// Convert qpp::cmat to std::vector<std::vector<complexNumber>>
matrix2d QppQVM::convertToMatrix2D(const qpp::cmat& eigenMatrix) {
	matrix2d result;

	for (Eigen::Index i = 0; i < eigenMatrix.rows(); ++i) {
		std::vector<complexNumber> row;
		for (Eigen::Index j = 0; j < eigenMatrix.cols(); ++j) {
			complexNumber cn;
			cn.a = eigenMatrix(i, j).real();
			cn.b = eigenMatrix(i, j).imag();
			row.push_back(cn);
		}
		result.push_back(row);
	}

	return result;
}

void QppQVM::setCurrentState(const qpp::ket &psi) {
	this->currentState.states = QppQVM::convertToStdVector(psi);	
}

/*
std::vector<std::complex<double>> QppQVM::getQubitStateVector(const QEngine& quantumSystem, int qubitIndex) {
	// Get the ket psi vector representing the state of the quantum system
	const ket& psi = quantumSystem.get_psi();

	// Number of qubits in the system
	int numQubits = quantumSystem.num_qubits();

	// Number of basis states for the entire system
	int numBasisStates = psi.size();

	// Check if the qubitIndex is valid
	if (qubitIndex < 0 || qubitIndex >= numQubits) {
	//	cerr << "Invalid qubit index." << endl;
		return std::vector<std::complex<double>>();  // Return an empty vector indicating an error
	}

	// Number of basis states for a single qubit
	int numBasisStatesPerQubit = 1 << (numQubits - 1);

	// Initialize the state vector for the specific qubit
	std::vector<std::complex<double>> qubitStateVector(2);

	// Extract amplitudes for the specified qubit
	for (int i = 0; i < numBasisStates; ++i) {
		// Check if the qubit is in state |0?
		if ((i / numBasisStatesPerQubit) % 2 == 0) {
			qubitStateVector[0] += psi[i];
		}
		// Check if the qubit is in state |1?
		else {
			qubitStateVector[1] += psi[i];
		}
	}

	// Normalize the state vector
	double norm = sqrt(norm(qubitStateVector[0]) + norm(qubitStateVector[1]));
	qubitStateVector[0] /= norm;
	qubitStateVector[1] /= norm;

	return qubitStateVector;
}*/