/*
 * Copyright (c) 2024 Quantag IT Solutions GmbH
 *
 * This source code is licensed under the MIT license found in the
 * LICENSE file in the root directory of this source tree.
 */

#pragma once

#include "interfaces/ifrontend.h"
#include "nlohmann/json.hpp"

class WebFrontend : public IFrontend {
public:
	WebFrontend();
	~WebFrontend();

	int loadCode(const std::string& sourceCode);
	int updateState(const FrontState& state);

protected:
	int send(const nlohmann::json& _data);


};

