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
	static std::string  decode64(const std::string& val);

	static int fileExists(const std::string& filePath);

	static std::string getShortName(const std::string& fileName);
	static int calcNumberOfLines(const std::string& sourceCode);
	static std::string complex2str(complexNumber a);
	static std::string toBinaryString(unsigned char val, size_t n);
	static std::string intToString(int n);
		
	static std::string executePythonCode(const std::string& sourceCode, PythonFramework fr);
//	static bool isOpenQASMCode(const std::string& code);

	static CodeType detectCodeType(const std::string& sourceCode);
	static bool containsPythonKeywords(const std::string& sourceCode);
	static bool containsOpenQASMKeywords(const std::string& sourceCode);
	static std::string vectorToString(const std::vector<int> data);

	static PythonFramework detectPythonFramework(const std::string& src);
	static std::string getFileNameFromFullPath(const std::string& fullPath);
	
	static std::string execute(const std::string& cmd);
	static CommandResult exec2(const std::string& command);

	static std::string findServerFile(const std::string& sessionFolder, const std::string& fileName);
	static std::string getFileNameWithParent(const std::string& fullPath);
	static std::string replaceChar(const std::string& input, char oldChar, char newChar);
	static std::string lastFrom(const std::string& str, size_t n);
	static std::string getPlainTextFromHTML(const std::string& html);
	static std::string getPreSpaces(const std::string& str);
	static int getLastLineWithoutPrespaces(const std::vector<std::string>& lines);
	static std::vector<std::string> cutArray(const std::vector<std::string>& lines, int endLine);
	static std::string combineVector(const std::vector<std::string>& lines);
	static std::vector<std::string> removePreSpaces(const std::vector<std::string>& lines, const std::string& preSpace);

	static void detectCommentLines(const std::vector<std::string>& lines, std::vector<int> &data);
	static int  getNextLine(int currentLine, const std::vector<CodeLine>& lines, int type);
	static int  getFirstLine(const std::vector<CodeLine>& lines, int type);

	static bool isCommentLine(const std::string& line, bool& inBlockComment);

	static void parseCode(const std::string& code, std::vector<CodeLine>& parsedCode, CodeType type);
	static void logSourceCode(const std::vector<CodeLine>& parsedCode);

	static int isExecutable(const std::string& line, CodeType type);
	static int isExecutableLineOpenQASM(const std::string& line);

};
