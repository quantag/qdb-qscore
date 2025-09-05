
#pragma once

#include "../interfaces/iqvm.h"

class ConfigLoader;
class PythonProcessor;
class IFrontend;

class BaseQVM : public IQVM {
public:
	void updateProcessor(CodeFramework framework);
	int getSourceLines();
	void setWSSession(WSSession* wsSession);
	int prepareSource(const std::string& fileName,
		const std::string& sessionId,
		LaunchStatus& status,
		std::string& preparedSource);

protected:
	PythonProcessor* processor;
	ConfigLoader* cfg;
	IFrontend* frontend;
};
