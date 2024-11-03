
#include "QppQVM.h"

#include "../Log.h"
#include "../ws/WSServer.h"
#include "../Utils.h"

#include "../WebFrontend.h"
#include "../QiskitProcessor.h"
#include "../TketProcessor.h"


#define DEMO_FILE		"/home/qbit/qasm/file1.qasm"
#define SOURCE_FOLDER	"/var/dap/"

QppQVM::QppQVM() : engine(NULL) {
	this->frontend = new WebFrontend();
	this->sourceCodeParsed = 0;
	processor = new QiskitProcessor();
}

QppQVM::~QppQVM() {
	SAFE_DELETE(engine);
	SAFE_DELETE(frontend);
	delete processor;
}

void QppQVM::setWSSession(WSSession* ws) {
	LOGI("setWSSession");
	this->frontend->setWSSession(ws);
}

int QppQVM::loadSourceCode(const std::string& fileName, const std::string& sessionId, LaunchStatus& status) {
	LOGI("[%s] [%s]", fileName.c_str(), sessionId.c_str());

	int ret = ERR_OK;
	status.pythonFramework = eUnknownFramework;
	status.codeType = eUnknown;

	this->sourceCodeParsed = 0;
	this->sourceCodePerLines.clear();

	sourceCode = "";
	std::string file = fileName;

	if (!Utils::fileExists(file)) {
		// try to find on server folder
		std::string defaultFolder = SOURCE_FOLDER + std::string("default");
		std::string serverFile = Utils::findServerFile(defaultFolder, file);
		if (Utils::fileExists(serverFile)) {
			LOGI("Found Server File in default folder '%s'", serverFile.c_str());

		}
		else {
			std::string sessionFolder = SOURCE_FOLDER + sessionId;
			serverFile = Utils::findServerFile(sessionFolder, file);
		}

		if (!Utils::fileExists(serverFile)) {
			LOGI("Server File '%s' not exists", serverFile.c_str());

			LOGI("File [%s] not exist, use demo file [%s]", fileName.c_str(), DEMO_FILE);
			file = DEMO_FILE;
			ret = ERR_DEMOFILE;

			status.serverFileFound = 0;
		}
		else {
			status.serverFileFound = 1;

			LOGI("Server File '%s' exists", serverFile.c_str());
			file = serverFile;
		}
	}

	if (!Utils::fileExists(file) ) {
		LOGI("File '%s' not exists", file.c_str());
		return ERR_NOFILE;
	}
	else {
		LOGI("File '%s' exist !", file.c_str());
		if(ret!= ERR_DEMOFILE) ret = ERR_OK;
	}

	sourceCode = Utils::loadFile(file);
	LOGI("Loaded %u bytes from [%s]", sourceCode.size(), file.c_str());

	// store original sources
	this->originalSourceCode = sourceCode;

	status.codeType = Utils::detectCodeType(sourceCode);
	LOGI("Source code type: %d", status.codeType);

	Utils::parseCode(sourceCode, originalParsedCode, status.codeType);
//	Utils::logSourceCode(originalParsedCode);

	switch (status.codeType) {
		case CodeType::ePython:
		{
			LOGI("Recognized Python source");
			status.pythonFramework = Utils::detectPythonFramework(sourceCode);
			LOGI("Recognized Python framework: %d", status.pythonFramework);
			updateProcessor(status.pythonFramework);
		
			ScriptExecResult result = processor->parsePythonToOpenQASM(sourceCode, sessionId);
			if (result.status!=0) {
				LOGE(">>> Parser returned error in HTML format");
				status.errorMessage = Utils::getPlainTextFromHTML(result.err);
				return 1;
			}
			else {
				this->sourceCode = result.res;
			}
			break;
		}
		case CodeType::eOpenQASM:
		{
			LOGI("Recognized OpenQASM source");
			ScriptExecResult result = processor->renderOpenQASMCircuit(sourceCode, sessionId);
			if (result.status != 0) {
				LOGE(">>> Render OpenQASM failed");
				status.errorMessage = "Rendering OpenQASM circuit failed : " + result.err;
				return 1;
			}
			break;
		}
			default:
				LOGE("Not recognized source code type");
	}

	int nLines = Utils::parseSourcePerLines(this->sourceCode, this->sourceCodePerLines);
	LOGI("Parsed lines: %d", nLines);

	this->currentState.currentLine = Utils::getFirstLine(this->originalParsedCode, 2) + 1;
	int ret1 = frontend->loadCode(this->sourceCode);
	LOGI("frontend.loadCode ret %d", ret1);

	try {
		LOGI("Trying to parse OpenQASM: '%s'", this->sourceCode.c_str());

		std::istringstream stringStream(this->sourceCode);
		circuit = std::make_unique<QCircuit>(qasm::read(stringStream));

		this->nQubits = circuit->get_nq();
		LOGI("Created QCircuit from file '%s', nQubits = %u", file.c_str(), this->nQubits);
		this->sourceCodeParsed = 1;
	}
	catch (qasmtools::parser::ParseError e) {
		LOGE("Error parsing OpenQASM from file [%s]. [%s]", file.c_str(), (e.what()!=NULL) ? e.what() : "");
		status.errorMessage = (e.what() != NULL) ? e.what() : "Parsing error";
	}
	catch (...) {
		// Catch any other type of exception
		LOGE("Caught unknown exception");
		status.errorMessage = "Unknown exception occurred";
	}

	return ret;
}


void QppQVM::updateProcessor(PythonFramework framework) {
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

int QppQVM::run(const std::string& fileName, const std::string& sessionId, LaunchStatus& status) {
	LOGI("%s [%s]", fileName.c_str(), sessionId.c_str());

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
	LOGI("%s [%s]", fileName.c_str(), sessionId.c_str());

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

int QppQVM::getSourceLines() {
	return Utils::calcNumberOfLines(this->sourceCode);
}

// Execute next line
long long QppQVM::stepForward() {
	LOGI("");

	if (!circuit || !this->sourceCodeParsed) {
		LOGI("Source code not parsed. Simulate. Line = %d", ++this->currentState.currentLine);
		return 0;
	}

	if (mIt != circuit->end()) {
		LOGI("Executing next line.. %d", this->currentState.currentLine);

		//this->currentState.currentLine ++; // if comments, then skip them.. 

		Utils::logSourceCode(originalParsedCode);
		LOGI("currentLine before getNextLine = %d", this->currentState.currentLine);
		this->currentState.currentLine = Utils::getNextLine(this->currentState.currentLine - 1, this->originalParsedCode, 2) + 1; // in UI line numbers starts from 1..
		LOGI("currentLine after getNextLine = %d", this->currentState.currentLine);

		this->currentState.code = Utils::encode64( this->sourceCode );

	//	if(this->getSourceLines()>0)
	//		this->currentState.currentLine %= this->getSourceLines();


		try {
			auto start = std::chrono::high_resolution_clock::now();
			engine->execute( mIt++ ); // crash

			qpp::ket psi = engine->get_psi();
//			cmat rho = prj(psi);

			setCurrentState(psi);	
			// const States& st = States::get_instance();  ?

			int ret1 = frontend->updateState(currentState);
			LOGI("frontend.updateState ret %d", ret1);

			auto stop = std::chrono::high_resolution_clock::now();
			auto duration = std::chrono::duration_cast<std::chrono::microseconds>(stop - start);
			LOGI( "Execution time: %ld ms", duration.count());
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