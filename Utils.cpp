
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

using namespace std;

// trim from start (in place)
static inline void ltrim(std::string& s) 
{
    s.erase(s.begin(), std::find_if(s.begin(), s.end(), [](unsigned char ch) {
        return !std::isspace(ch);
        }));
}

// trim from end (in place)
static inline void rtrim(std::string& s) 
{
    s.erase(std::find_if(s.rbegin(), s.rend(), [](unsigned char ch) {
        return !std::isspace(ch);
        }).base(), s.end());
}

void Utils::trim(std::string& s) 
{
	rtrim(s);
	ltrim(s);
}


std::vector<std::string> Utils::tokenize(const std::string& str, const std::string& sep) 
{
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

std::string Utils::loadFile(const std::string& fileName) 
{
    std::ifstream file(fileName);

    if (!file.is_open()) 
    {
       // std::cerr << "Error opening file: " << fileName << std::endl;
        return "";
    }

    std::stringstream buffer;
    buffer << file.rdbuf();
    file.close();

    return buffer.str();
}

std::vector<std::string> Utils::parseSourcePerLines(const std::string& source) 
{
    std::vector<std::string> lines;
    std::istringstream sourceStream(source);
    std::string line;

    while (std::getline(sourceStream, line)) {
        lines.push_back(line);
    }

    return lines;
}

void Utils::logSource(const std::vector<std::string>& src) 
{
    for (int i = 0; i < src.size(); i++) 
    {
        LOGI("line %d. [%s]", i+1, src.at(i).c_str());
    }
}

std::string  Utils::encode64(const std::string& val) 
{
    using namespace boost::archive::iterators;
    using It = base64_from_binary<transform_width<std::string::const_iterator, 6, 8>>;
    auto tmp = std::string(It(std::begin(val)), It(std::end(val)));
    return tmp.append((3 - val.size() % 3) % 3, '=');
    return val;
}

int Utils::fileExists(const std::string& filePath) 
{
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