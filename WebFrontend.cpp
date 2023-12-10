#include "WebFrontend.h"

#include "Log.h"
#include "ws/WSServer.h"
#include "Utils.h"


WebFrontend::WebFrontend() {
	this->wsServer = NULL;
}

WebFrontend::~WebFrontend() {

}

int WebFrontend::loadCode(const std::string& sourceCode) {
	LOGI("");

	if (!wsServer) return 1;

	nlohmann::json json;
	json["command"] = "load";
	
	std::string encodedSourceCode = Utils::encode64(sourceCode);
	json["code"] = encodedSourceCode;

	return send(json);
}


void to_json(nlohmann::json& j, const complexNumber& c) {
	j = nlohmann::json{ {"a", c.a}, {"b", c.b} };
}
void to_json(nlohmann::json& j, const matrix2d& matrix) {
	for (const auto& row : matrix) {
		j.push_back(row);
	}
}

int WebFrontend::updateState(const FrontState& state) {
	LOGI("line = %d", state.currentLine);
	if (!wsServer) return 1;

	nlohmann::json json;
	json["command"] = "update";

	json["line"] = state.currentLine;
	json["states"] = state.states;
	json["matrix"] = state.densityMatrix;

	return send(json);
}

int WebFrontend::send(const nlohmann::json& _data) {
	std::string data = _data.dump();

	int res = wsServer->send(data);
	return res;
}
