
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

	virtual int run(const std::string& code,
		const std::string& path,
		LaunchStatus& status) = 0;

protected:
	PythonProcessor* processor;
	IFrontend* frontend;
};
