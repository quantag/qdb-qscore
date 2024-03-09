#pragma once

#include <string>
#include <vector>

#include "Typedefs.h"


class Utils {
public:

	static void trim( std::string& str);
	static std::vector<std::string> tokenize(const std::string& str, const std::string& sep);
	static std::string loadFile(const std::string& filePath);
	static int parseSourcePerLines(const std::string& source, std::vector<std::string>& data);
	static void logSource(const std::vector<std::string>& src);

	static std::string  encode64(const std::string& val);
	static int fileExists(const std::string& filePath);

	static std::string getShortName(const std::string& fileName);
	static int calcNumberOfLines(const std::string& sourceCode);
	static std::string complex2str(complexNumber a);
	static std::string toBinaryString(unsigned char val, size_t n);
	static std::string intToString(int n);
		
	static std::string executePythonCode(const std::string& sourceCode, PythonFramework fr);
	static bool isOpenQASMCode(const std::string& code);

	static CodeType detectCodeType(const std::string& sourceCode);
	static bool containsPythonKeywords(const std::string& sourceCode);
	static bool containsOpenQASMKeywords(const std::string& sourceCode);
	static std::string vectorToString(const std::vector<int> data);

	static PythonFramework detectPythonFramework(const std::string& src);
	static std::string getFileNameFromFullPath(const std::string& fullPath);
	
	static std::string execute(const std::string& cmd);
	static CommandResult exec2(const std::string& command);

};
