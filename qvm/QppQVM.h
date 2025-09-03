/*
 * Copyright (c) 2024 Quantag IT Solutions GmbH
 *
 * This source code is licensed under the MIT license found in the
 * LICENSE file in the root directory of this source tree.
 */


#pragma once

#include "BaseQVM.h"
#include <qpp.h>

using namespace qpp;

class WSSession;
class IFrontend;
class PythonProcessor;
class ConfigLoader;

class QppQVM : public BaseQVM {
public:
	QppQVM();
	QppQVM(ConfigLoader *cfg);
	~QppQVM();

	int loadSourceCode(const std::string& fileName, const std::string& sessionId, LaunchStatus& status);
	int run(const std::string& fileName, const std::string& sessionId, LaunchStatus& status);
	int debug(const std::string& fileName, const std::string& sessionId, LaunchStatus& status);

	virtual std::string getQVMName() {
		return "QPP 1.0.11";
	}


	double stepForward();

	static std::vector<complexNumber> convertToStdVector(const qpp::ket& eigenVector);
	static matrix2d convertToMatrix2D(const qpp::cmat& eigenMatrix);

private:
	// Smart pointer to store QCircuit object
	std::unique_ptr<QCircuit> circuit;

	QEngine* engine;

	QCircuit::iterator mIt; // current state
	void setCurrentState(const qpp::ket& psi);

};
