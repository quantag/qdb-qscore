#pragma once

#include <string>

// interface to QVM
class IQVM {
public:
	virtual int loadSourceCode(const std::string& fileName) = 0;

	virtual int run(const std::string& fileName) = 0;
	virtual int debug(const std::string& fileName) = 0;

	virtual int getSourceLines() = 0;
	virtual void stepForward() = 0;
};