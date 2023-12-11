
#include "QppQVM.h"


#include "../Log.h"
#include "../ws/WSServer.h"
#include "../Utils.h"

#include "../WebFrontend.h"

#define DEMO_FILE "/home/qbit/qasm/file1.qasm"

QppQVM::QppQVM(WSServer* ws) : circuit(NULL), engine(NULL) {
	this->frontend = new WebFrontend();
	this->frontend->setWSServer(ws);
}

QppQVM::~QppQVM() {
	SAFE_DELETE(circuit);
	SAFE_DELETE(engine);
	SAFE_DELETE(frontend);

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

	this->currentState.currentLine = 0;
	int ret1 = frontend->loadCode(sourceCode);
	LOGI("frontend.loadCode ret %d", ret1);

	try {
		circuit = qasm::readFromFile(file);
		this->nQubits = circuit->get_nq();
	}
	catch (...) {
		LOGE("Error during creation of Circuit from file %s", file.c_str());
	}

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

	mIt = circuit->begin();
	LOGI("Iterator initialized");

	return 0;
}

int QppQVM::getSourceLines() {
	return Utils::calcNumberOfLines(this->sourceCode);
}

// Execute next line
void QppQVM::stepForward() {
	LOGI("");

	if (mIt != circuit->end()) {
		LOGI("Executing next line.. %d", this->currentState.currentLine);
		this->currentState.currentLine ++;

		if(this->getSourceLines()>0)
			this->currentState.currentLine %= this->getSourceLines();

		try {
			engine->execute( mIt++ ); // crash

			qpp::ket psi = engine->get_psi();
//			cmat rho = prj(psi);

			setCurrentState(psi);	
			// const States& st = States::get_instance();  ?

			int ret1 = frontend->updateState(currentState);
			LOGI("frontend.updateState ret %d", ret1);
		}
		catch (...) {
			LOGE("Error executing next line");
		}

	}
	else {
		LOGI("Reached end of circuit..");
	}
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