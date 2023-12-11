#pragma once

#include <string>
#include <vector>

#include "Typedefs.h"

class Utils {
public:

	static void trim( std::string& str);
	static std::vector<std::string> tokenize(const std::string& str, const std::string& sep);
	static std::string loadFile(const std::string& filePath);
	static std::vector<std::string> parseSourcePerLines(const std::string& source);
	static void logSource(const std::vector<std::string>& src);

	static std::string  encode64(const std::string& val);
	static int fileExists(const std::string& filePath);

	static std::string getShortName(const std::string& fileName);
	static int calcNumberOfLines(const std::string& sourceCode);
	static std::string complex2str(complexNumber a);
	static std::string toBinaryString(unsigned char val, size_t n);

};
