#include "WebFrontend.h"

#include "Log.h"
#include "ws/WSSession.h"
#include "Utils.h"


WebFrontend::WebFrontend() {
	this->wsSession = nullptr;
}

WebFrontend::~WebFrontend() {

}

int WebFrontend::loadCode(const std::string& sourceCode) {
	LOGI("");

	if (!wsSession) return 1;

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
	if (!wsSession) return 1;

	nlohmann::json json;
	json["command"] = "update";

	json["line"] = state.currentLine;
	json["states"] = state.states;
	json["code"] = state.code;

	return send(json);
}

int WebFrontend::send(const nlohmann::json& _data) {
	if (!wsSession)
		return 1;

	std::string data = _data.dump();
	LOGI("FRONTEND>> '%s'", data.c_str());

	wsSession->send(data);
	return 0;
}
