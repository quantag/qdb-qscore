
#include "TketProcessor.h"

#include "Log.h"
#include "Utils.h"

TketProcessor::TketProcessor() : PythonProcessor(eTket) {
}

TketProcessor::~TketProcessor() {
}

/**
	from pytket.circuit import Circuit
	c = Circuit(3, 2)
*/
void TketProcessor::findAllQuantumCircuitDeclarations(std::vector<int>& result) {
	int n = 0;
	for (std::string& line : this->sourceLines) {
		if (line.find("Circuit") != std::string::npos && line.find("import") == std::string::npos) {
			result.push_back(n);
		}
		n++;
	}
}

ScriptExecResult TketProcessor::parsePythonToOpenQASM(const std::string& sourceCode, const std::string& sessionId) {
	LOGI("%s [%s]", sourceCode.c_str(), sessionId.c_str());

	Utils::parseSourcePerLines(sourceCode, sourceLines);
	Utils::logSource(sourceLines);

	this->removeAllPrints();

	std::vector<int> linesWithQuantumCircuit;
	findAllQuantumCircuitDeclarations(linesWithQuantumCircuit);

	if (!linesWithQuantumCircuit.empty()) {
		LOGI("Found Circuits at lines: %s", Utils::vectorToString(linesWithQuantumCircuit).c_str());

		for (int line : linesWithQuantumCircuit) {
			std::string qcName = getQuantumCircuitName(line);
			LOGI("Circuit name at line %d is '%s'", line, qcName.c_str());

			int lastLine = findLastUsage(qcName);
			if (lastLine > 0) {
				LOGI("Last usage of QC '%s' on line %d", qcName.c_str(), lastLine);
				// qasm_str = circuit_to_qasm_str(circ, header="hqslib1")
				
				//this->sourceLines.insert(sourceLines.begin() + lastLine + 1, "code777=circuit_to_qasm_str(" + qcName + ", header=\"hqslib1\")");
				this->sourceLines.insert(sourceLines.begin() + lastLine + 1, std::string(BRIDGE_VAR) + "=circuit_to_qasm_str(" + qcName + ")");

				this->sourceLines.insert(sourceLines.begin() + lastLine + 1, 
					"s2f(render_circuit_as_html(" + qcName + std::string("),'") + SERVER_IMAGE_FOLDER + sessionId + ".html')");
				 
			}
		}
	}
	else {
		LOGI("No QuantumCircuit declarations found");
	}

	int lastImportLine = findLastImportLine();
	LOGI("Last import line: %d", lastImportLine);
	if (lastImportLine < 0)
		lastImportLine = 0;

	this->sourceLines.insert(sourceLines.begin() + lastImportLine + 1, "def s2f(text, filename):");
	this->sourceLines.insert(sourceLines.begin() + lastImportLine + 2, "    with open(filename, \"w\") as file:");
	this->sourceLines.insert(sourceLines.begin() + lastImportLine + 3, "        file.write(text)");

	if (!importPresent("pytket.qasm", "circuit_to_qasm_str"))
		addImport("pytket.qasm", "circuit_to_qasm_str"); 

	if (!importPresent("pytket.circuit.display", "render_circuit_as_html"))
		addImport("pytket.circuit.display", "render_circuit_as_html");

	std::string updatedSource = Utils::combineVector(this->sourceLines);
	LOGI("Updated sources:\n%s", updatedSource.c_str());

	ScriptExecResult out = restClient.execCode(updatedSource);
	LOGI("rest api returned status '%d'", out.status);

	return out;
}