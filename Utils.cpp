
#include "Utils.h"

#include <algorithm> 
#include <cctype>
#include <locale>

#include <iostream>
#include <fstream>
#include <sstream>

#include <boost/archive/iterators/binary_from_base64.hpp>
#include <boost/archive/iterators/base64_from_binary.hpp>
#include <boost/archive/iterators/transform_width.hpp>
#include <boost/algorithm/string.hpp>

#include "Log.h"
#include <bitset>

using namespace std;

// trim from start (in place)
static inline void ltrim(std::string& s) {
    s.erase(s.begin(), std::find_if(s.begin(), s.end(), [](unsigned char ch) {
        return !std::isspace(ch);
        }));
}

// trim from end (in place)
static inline void rtrim(std::string& s) {
    s.erase(std::find_if(s.rbegin(), s.rend(), [](unsigned char ch) {
        return !std::isspace(ch);
        }).base(), s.end());
}

void Utils::trim(std::string& s) {
	rtrim(s);
	ltrim(s);
}


std::vector<std::string> Utils::tokenize(const std::string& str, const std::string& sep) {
    std::vector<std::string> tokens;
    size_t startPos = 0;
    size_t foundPos = str.find_first_of(sep, startPos);

    while (foundPos != std::string::npos) {
        // Extract the token from the current position to the found position
        std::string token = str.substr(startPos, foundPos - startPos);

        // Add the token to the vector
        if(!token.empty())
            tokens.push_back(token);

        // Move the start position to the next character after the separator
        startPos = foundPos + 1;

        // Find the next occurrence of a separator
        foundPos = str.find_first_of(sep, startPos);
    }

    // Add the last token (or the only token if no separator is found)
    std::string lastToken = str.substr(startPos);
    
    if (!lastToken.empty())
        tokens.push_back(lastToken);

    return tokens;
}

std::string Utils::loadFile(const std::string& fileName) {
    std::ifstream file(fileName);

    if (!file.is_open()) {
       // std::cerr << "Error opening file: " << fileName << std::endl;
        return "";
    }

    std::stringstream buffer;
    buffer << file.rdbuf();
    file.close();

    return buffer.str();
}

int Utils::parseSourcePerLines(const std::string& source, std::vector<std::string>& lines) {
    std::istringstream sourceStream(source);
    std::string line;
    lines.clear();

    while (std::getline(sourceStream, line)) {
        lines.push_back(line);
    }
    return (int) lines.size();
}

void Utils::logSource(const std::vector<std::string>& src) {
    for (int i = 0; i < src.size(); i++) {
        LOGI("line %d. [%s]", i+1, src.at(i).c_str());
    }
}

std::string  Utils::encode64(const std::string& val) {
    using namespace boost::archive::iterators;
    using It = base64_from_binary<transform_width<std::string::const_iterator, 6, 8>>;
    auto tmp = std::string(It(std::begin(val)), It(std::end(val)));
    return tmp.append((3 - val.size() % 3) % 3, '=');
 //   return val;
}

int Utils::fileExists(const std::string& filePath) {
    std::ifstream file(filePath.c_str());
    return file.good() ? 1 : 0;
}


 std::string Utils::getShortName(const std::string& fileName) {
    // Find the last occurrence of path separator
    size_t lastSeparator = fileName.find_last_of("/\\");

    // Extract the file name using substr
    if (lastSeparator != std::string::npos) {
        return fileName.substr(lastSeparator + 1);
    }

    // If no separator found, return the original string
    return fileName;
}

 int Utils::calcNumberOfLines(const std::string& sourceCode) {
     int numberOfLines = 0;
     bool isNewLine = true;

     for (char c : sourceCode) {
         if (c == '\n' || c == '\r') {
             if (!isNewLine) {
                 isNewLine = true;
                 ++numberOfLines;
             }
         }
         else {
             isNewLine = false;
         }
     }

     // Check if the last line doesn't end with a newline character
     if (!isNewLine && !sourceCode.empty()) {
         ++numberOfLines;
     }

     return numberOfLines;
 }

 std::string Utils::complex2str(complexNumber z) {
     std::string res = std::to_string(z.a) + " + i" + std::to_string(z.b);
     return res;
 }


 std::string Utils::toBinaryString(unsigned char val, size_t n) {
     // Use bitwise shift and bitwise OR to extract each bit of the value
     std::bitset<8> bits(val);
     std::string binaryString = bits.to_string();

     // If the specified length is greater than the actual length, pad with zeros
     if (n > 8U) {
         binaryString = std::string(n - 8, '0') + binaryString;
     }

     // If the specified length is less than the actual length, truncate
     if (n < 8U) {
         binaryString = binaryString.substr(8 - n);
     }

     return binaryString;
 }

 std::string Utils::intToString(int n) {
     return std::to_string(n);
 }

#define TEMP_FILE "tempPythonScript.py"

std::string Utils::executePythonCode(const std::string& sourceCode) {
    LOGI("%s", sourceCode.c_str());

    // Create a temporary file to store the Python code
    std::ofstream tempFile(TEMP_FILE);
    tempFile << sourceCode;
    tempFile.close();

    char buffer[128];
    std::string result = "";

    std::string cmd = "C:\\work\\quantum\\qiskit\\Scripts\\activate && python ";
    cmd += TEMP_FILE;

    FILE* pipe = _popen(cmd.c_str(), "r");
    if (!pipe) {
        LOGE("popen() failed!");
        std::remove(TEMP_FILE);
        return "";
    }
    try {
        while (fgets(buffer, sizeof buffer, pipe) != NULL) {
            result += buffer;
        }
    }
    catch (...) {
        _pclose(pipe);
        std::remove(TEMP_FILE);

        return "";
    }
    _pclose(pipe);
    std::remove(TEMP_FILE);

    return result;
 }

#include <iostream>
#include <regex>

CodeType Utils::detectCodeType(const std::string& sourceCode) {
    if (containsPythonKeywords(sourceCode)) {
        return CodeType::Python;
    }
    else if (containsOpenQASMKeywords(sourceCode)) {
        return CodeType::OpenQASM;
    }
    else {
        return CodeType::Unknown;
    }
}


bool Utils::containsPythonKeywords(const std::string& sourceCode) {
    static const std::regex pythonKeywordsRegex("(def|import|print)");

    return std::regex_search(sourceCode, pythonKeywordsRegex);
}

bool Utils::containsOpenQASMKeywords(const std::string& sourceCode) {
    static const std::regex openQASMKeywordsRegex("(qreg|creg|H|X|Y|Z|measure)");

    return std::regex_search(sourceCode, openQASMKeywordsRegex);
}
