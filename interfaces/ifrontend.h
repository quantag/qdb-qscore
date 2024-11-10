/*
 * Copyright (c) 2024 Quantag IT Solutions GmbH
 *
 * This source code is licensed under the MIT license found in the
 * LICENSE file in the root directory of this source tree.
 */

#pragma once

#include <string>
#include <vector>
#include "../Typedefs.h"

typedef std::vector< std::vector<complexNumber>>  matrix2d;

// current state show on frontend
struct FrontState {
	int currentLine;

	std::vector<complexNumber> states;
	std::string code;
//	matrix2d densityMatrix;
};


class WSSession;
// interface to web frontend
class IFrontend {
public:
	virtual int loadCode(const std::string &sourceCode) = 0;
	virtual int updateState(const FrontState &state) = 0;

	virtual void setWSSession(WSSession* ws) {
		this->wsSession = ws;
	}

protected:
	WSSession* wsSession;
};