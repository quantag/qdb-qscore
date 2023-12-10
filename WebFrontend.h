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

