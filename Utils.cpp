/*
 * Copyright (c) 2024 Quantag IT Solutions GmbH
 *
 * This source code is licensed under the MIT license found in the
 * LICENSE file in the root directory of this source tree.
 */


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

#include <iostream>
#include <regex>
#include <filesystem>

#include <nlohmann/json.hpp>


#ifdef WIN32
    #define QISKIT_VENV "C:\\work\\quantum\\qiskit\\Scripts\\activate"
    #define TEMP_FILE   "tempPythonScript.py"
#else
    #define QISKIT_VENV "source /var/qiskit/bin/activate"
    #define TEMP_FILE   "/tmp/tempPythonScript.py"
#endif

#define DELETE_TMP


#ifdef WIN32
    #define PCLOSE _pclose
    #define POPEN _popen
#else
    #define PCLOSE pclose
    #define POPEN popen
#endif

#include <array>

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
        if (line.empty())
            continue;

        if(line.at(0)!='#')
            lines.push_back(line);
    }
    return (int) lines.size();
}

void Utils::logSource(const std::vector<std::string>& src) {
    for (size_t i = 0; i < src.size(); i++) {
        LOGD("line %d. [%s]", i, src.at(i).c_str());
    }
}

std::string  Utils::encode64(const std::string& val) {
    using namespace boost::archive::iterators;
    using It = base64_from_binary<transform_width<std::string::const_iterator, 6, 8>>;
    auto tmp = std::string(It(std::begin(val)), It(std::end(val)));
    return tmp.append((3 - val.size() % 3) % 3, '=');
}

std::string Utils::decode64(const std::string& val) {
    using namespace boost::archive::iterators;
    typedef transform_width<binary_from_base64<std::string::const_iterator>, 8, 6> It;

    // Calculate the size of the decoded string
    auto len = val.size();
    size_t padding = 0;
    if (len > 0 && val[len - 1] == '=')
        padding++;
    if (len > 1 && val[len - 2] == '=')
        padding++;
    size_t outLen = len * 3 / 4 - padding;

    // Perform decoding
    std::stringstream os;
    std::copy(It(std::begin(val)), It(std::end(val)), std::ostream_iterator<char>(os));

    // Return the decoded string
    return os.str().substr(0, outLen);
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


std::string Utils::executePythonCode(const std::string& sourceCode, PythonFramework fr) {
    LOGI("framework = %u, '%s'", fr, sourceCode.c_str());

    // Create a temporary file to store the Python code
    std::ofstream tempFile(TEMP_FILE);
    tempFile << sourceCode;
    tempFile.close();

    std::string cmd = std::string(QISKIT_VENV) + " && python ";
    cmd += TEMP_FILE;

    LOGI("cmd = '%s'", cmd.c_str());
    std::string result = execute(cmd);

    LOGI("res = '%s'", result.c_str());

#ifdef DELETE_TMP
        std::remove(TEMP_FILE);
#endif

    return result;
 }

std::string Utils::execute(const std::string& cmd) {
    char buffer[1024];
    std::string result = "";

    LOGI("cmd = '%s'", cmd.c_str());

    FILE* pipe = POPEN(cmd.c_str(), "r");
    if (!pipe) {
        LOGE("popen() failed!");

        return "";
    }
    try {
        while (fgets(buffer, sizeof buffer, pipe) != NULL) {
            result += buffer;
        }
    }
    catch (...) {
        PCLOSE(pipe);
        return "";
    }
    PCLOSE(pipe);
//    trim(result);
    return result;
}


CodeType Utils::detectCodeType(const std::string& sourceCode) {
    if (containsPythonKeywords(sourceCode)) {
        return CodeType::ePython;
    }
    else if (containsOpenQASMKeywords(sourceCode)) {
        return CodeType::eOpenQASM;
    }
    else {
        return CodeType::eUnknown;
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

std::string Utils::vectorToString(const std::vector<int> data) {
    std::string str = "";
    for (int val : data) {
        str += to_string(val) + " ";
    }
    return str;
}

PythonFramework Utils::detectPythonFramework(const std::string & src) {
    if (src.find("qiskit") != std::string::npos)
        return eQiskit;

    if (src.find("pytket") != std::string::npos)
        return eTket;

    return eGeneric;
}

std::string Utils::getFileNameFromFullPath(const std::string& fullPath) {
    size_t p1 = fullPath.find_last_of('/');
    if (p1 != std::string::npos) {
        p1++;
        return fullPath.substr(p1, fullPath.size() - p1);
    }

    return fullPath;
}

std::string Utils::lastFrom(const std::string& str, size_t n) {
    return str.substr(n, str.size() - n);
}

std::string Utils::getFileNameWithParent(const std::string& _fullPath) {
    std::string fullPath = replaceChar(_fullPath, '\\', '/');

    size_t p1 = fullPath.find_last_of('/');
    if (p1 == std::string::npos)
        return fullPath;

    size_t p2 = fullPath.substr(0, p1).find_last_of('/');
    if (p2 == std::string::npos)
        return lastFrom(fullPath, p1);

    return lastFrom(fullPath, p2+1);
}


CommandResult Utils::exec2(const std::string& command) {
    int exitcode = 255;
    std::array<char, 1024> buffer{};
    std::string result;
#ifdef _WIN32
#define popen _popen
#define pclose _pclose
#define WEXITSTATUS
#endif
    FILE* pipe = popen(command.c_str(), "r");
    if (pipe == nullptr) {
        throw std::runtime_error("popen() failed!");
    }
    try {
        std::size_t bytesread;
        while ((bytesread = fread(buffer.data(), sizeof(buffer.at(0)), sizeof(buffer), pipe)) != 0) {
            result += std::string(buffer.data(), bytesread);
        }
    }
    catch (...) {
        pclose(pipe);
        throw;
    }
    exitcode = WEXITSTATUS(pclose(pipe));
    return CommandResult{ result, exitcode };
}

std::string Utils::findServerFile(const std::string& sessionFolder, const std::string& _fileName) {
    std::string fileName = replaceChar(_fileName, '\\', '/');

    std::string serverFile = sessionFolder + "/" + Utils::getFileNameFromFullPath(fileName);

    LOGI("trying [%s]", serverFile.c_str());
    if (Utils::fileExists(serverFile))
        return serverFile;

    // step 1 folder deep
    serverFile = sessionFolder + "/" + Utils::getFileNameWithParent(fileName);
    LOGI("trying [%s]", serverFile.c_str());

    if (Utils::fileExists(serverFile))
        return serverFile;

    return serverFile;
}

std::string Utils::replaceChar(const std::string& input, char oldChar, char newChar) {
    std::string result = input;
    for (char& c : result) {
        if (c == oldChar) {
            c = newChar;
        }
    }
    return result;
}

std::string Utils::getPlainTextFromHTML(const std::string& html) {
    // Regular expression to match HTML tags
    std::regex tagRegex("<[^>]*>");

    // Replace all HTML tags with an empty string
    std::string plainText = std::regex_replace(html, tagRegex, "");

    // Return the plain text
    return plainText;
}

std::string Utils::getPreSpaces(const std::string& str) {
    std::string spaces;
    for (char c : str) {
        if (c == ' ' || c == '\t') {
            spaces += c;
        }
        else {
            break;
        }
    }
    return spaces;
}

int Utils::getLastLineWithoutPrespaces(const std::vector<std::string> &lines) {
    int endLine = 0;

    for (const std::string& line : lines) {
        if (Utils::getPreSpaces(line).empty()) {
            return endLine;
        }
        endLine++;
    }
    return endLine;
}

std::vector<std::string> Utils::cutArray(const std::vector<std::string>& lines, int endLine) {
    if (endLine >= 0 && endLine < lines.size()) {
        return std::vector<std::string>(lines.begin(), lines.begin() + endLine + 1);
    }
    else {
        // If endLine is out of range, return empty vector or throw an exception
        return std::vector<std::string>();
    }
}

std::string Utils::combineVector(const std::vector<std::string>& lines) {
    std::string res = "";
    for (const std::string& line : lines) {
        res += line + "\n";
    }
    return res;
}

std::vector<std::string> Utils::removePreSpaces(const std::vector<std::string>& lines, const std::string& preSpace) {
    std::vector<std::string> result;

    // Iterate over each line in the input vector
    for (const std::string& line : lines) {
        // Check if the line starts with the specified preSpace
        if (line.find(preSpace) == 0) {
            // If it does, remove the preSpace and add the modified line to the result vector
            result.push_back(line.substr(preSpace.length()));
        }
        else {
            // If it doesn't, just add the original line to the result vector
            result.push_back(line);
        }
    }

    return result;
}

bool Utils::isCommentLine(const std::string& line, bool& inBlockComment) {
    // Remove leading whitespace from the line
    size_t firstNonWhitespace = line.find_first_not_of(" \t");

    // If the line is empty or contains only whitespace, consider it as a comment
    if (firstNonWhitespace == std::string::npos) {
        return true;
    }

    // Check for multi-line comments
    if (inBlockComment) {
        // Check if the block comment ends in this line
        if (line.find("*/", firstNonWhitespace) != std::string::npos ||
            line.find("\"\"\"", firstNonWhitespace) != std::string::npos) {
            inBlockComment = false;
        }
        return true;
    }
    else {
        // Check if a block comment starts in this line
        if (line.find("/*", firstNonWhitespace) != std::string::npos ||
            line.find("\"\"\"", firstNonWhitespace) != std::string::npos) {
            inBlockComment = true;
            // Check if the block comment ends in the same line
            if (line.find("*/", firstNonWhitespace + 2) != std::string::npos ||
                line.find("\"\"\"", firstNonWhitespace + 3) != std::string::npos) {
                inBlockComment = false;
            }
            return true;
        }
    }

    // Check if the first non-whitespace character is '#' or if it starts with "//"
    if (line[firstNonWhitespace] == '#' ||
        (line.length() > firstNonWhitespace + 1 && line.substr(firstNonWhitespace, 2) == "//")) {
        return true; // It's a comment line
    }
    else {
        return false; // It's not a comment line
    }
}


void Utils::detectCommentLines(const std::vector<std::string>& lines, std::vector<int>& data) {
    // Clear the data vector to ensure it is empty before starting
    data.clear();

    // Variable to track if we are inside a block comment
    bool inBlockComment = false;

    // Iterate through each line in the provided vector
    for (const auto& line : lines) {
        // Use the helper method to determine if the line is a comment
        if (isCommentLine(line, inBlockComment)) {
            data.push_back(0); // It's a comment line
        }
        else {
            data.push_back(1); // It's not a comment line
        }
    }
}


int Utils::getNextLine(int currentLine, const std::vector<CodeLine>& lines, int type) {
    // Check if currentLine is within valid range
    if (currentLine < 0  || currentLine >= lines.size()) {
        return 0; // Invalid input
    }

    // Iterate through the lines starting from currentLine + 1
    for (int i = currentLine + 1; i < lines.size(); ++i) {
        if (lines[i].type == type) { // Check if it's a code line
            return i; // Return the index of the next code line
        }
    }

    // No more code lines found
    return 0;
}

int Utils::getFirstLine(const std::vector<CodeLine>& lines, int type) {
    // Iterate through the lines starting from currentLine + 1
    for (size_t i = 0; i < lines.size(); ++i) {
        if (lines[i].type == type) { // Check if it's a code line
            return i; // Return the index of the next code line
        }
    }

    // No more code lines found
    return 0;
}

// Method to parse code into a vector of CodeLine
void Utils::parseCode(const std::string& code, std::vector<CodeLine>& parsedCode, CodeType type) {
    // Clear the parsedCode vector to ensure it is empty before starting
    parsedCode.clear();

    // Variable to track if we are inside a block comment
    bool inBlockComment = false;

    // Create a string stream from the code to read it line by line
    std::istringstream stream(code);
    std::string line;

    // Iterate through each line in the code
    while (std::getline(stream, line)) {
        CodeLine codeLine;
        codeLine.line = line;
        if (isCommentLine(line, inBlockComment)) {
            codeLine.type = 0; // It's a comment line
        }
        else {
            codeLine.type = 1; // It's a code line
            if (isExecutable(line, type) || type==CodeType::ePython)
                codeLine.type = 2;
        }
        parsedCode.push_back(codeLine);
    }
}

int Utils::isExecutable(const std::string& line, CodeType type) {
    switch (type) {
    case CodeType::ePython:
        return 0;
    case CodeType::eOpenQASM:
        return isExecutableLineOpenQASM(line);
    }
    return 0;
}

void Utils::logSourceCode(const std::vector<CodeLine>& code) {
    for (size_t i = 0; i < code.size(); i++) {
        LOGI("line %u. [%s] [%d]", i, code.at(i).line.c_str(), code.at(i).type);

    }
}

int Utils::isExecutableLineOpenQASM(const std::string& line) {
    // Remove leading and trailing whitespace from the line
    size_t firstNonWhitespace = line.find_first_not_of(" \t");
    if (firstNonWhitespace == std::string::npos) {
        return 0; // Line is empty or contains only whitespace
    }

    std::string trimmedLine = line.substr(firstNonWhitespace);
    size_t lastNonWhitespace = trimmedLine.find_last_not_of(" \t");
    trimmedLine = trimmedLine.substr(0, lastNonWhitespace + 1);

    // Check if the line is a comment
    if (trimmedLine[0] == '/' && trimmedLine[1] == '/') {
        return 0; // It's a comment line
    }

    // Check if the line is a declaration or directive
    if (trimmedLine.rfind("OPENQASM", 0) == 0 || // Starts with "OPENQASM"
        trimmedLine.rfind("include", 0) == 0 ||  // Starts with "include"
        trimmedLine.rfind("qreg", 0) == 0 ||     // Starts with "qreg"
        trimmedLine.rfind("creg", 0) == 0 ||     // Starts with "creg"
        trimmedLine.rfind("gate", 0) == 0 ||     // Starts with "gate"
        trimmedLine.rfind("opaque", 0) == 0 ||   // Starts with "opaque"
        trimmedLine.rfind("measure", 0) == 0 ||  // Starts with "measure"
        trimmedLine.rfind("reset", 0) == 0) {    // Starts with "reset"
        return 0; // It's a non-executable line
    }

    // All other lines are considered executable actions
    return 1;
}

std::string Utils::getCodeTypeName(CodeType type) {
    switch (type) {
        case ePython: return "Python";
        case eOpenQASM: return "OpenQASM";
        case eUnknown: return "Unknown";
    }
    return "?";
}


int Utils::getFilesInFolder(const std::string& folderPath, std::vector<std::string>& files) {
   files.clear();  // Clear any existing content in the vector

    // Check if the folder path exists and is a directory
    if (!std::filesystem::exists(folderPath) || !std::filesystem::is_directory(folderPath)) {
        std::cerr << "Invalid folder path: " << folderPath << std::endl;
        return -1;  // Return -1 for invalid folder path
    }

    // Try to iterate over directory contents
    try {
        for (const auto& entry : std::filesystem::directory_iterator(folderPath)) {
            if (entry.is_regular_file()) {
                files.push_back(entry.path().string());
            }
        }
    }
    catch (const std::filesystem::filesystem_error& e) {
        std::cerr << "Filesystem error: " << e.what() << std::endl;
        return -2;  // Return -2 for filesystem errors
    }

    return 0;  // Return 0 if operation was successful
}

std::string Utils::getPythonFrameworkName(PythonFramework type) {
    switch (type) {
        case eGeneric:  return "Generic";
        case eQiskit:   return "Qiskit";
        case eTket:     return "pyTket";
    }
    return "?";
}

#ifdef _WIN32
#include <intrin.h>  // For __cpuid intrinsic on Windows

std::string Utils::getCpuInfo() {
    // Get the CPU brand string
    std::array<int, 4> cpuInfo;
    std::array<char, 48> brand;
    __cpuid(cpuInfo.data(), 0x80000002);
    memcpy(brand.data(), cpuInfo.data(), sizeof(cpuInfo));
    __cpuid(cpuInfo.data(), 0x80000003);
    memcpy(brand.data() + 16, cpuInfo.data(), sizeof(cpuInfo));
    __cpuid(cpuInfo.data(), 0x80000004);
    memcpy(brand.data() + 32, cpuInfo.data(), sizeof(cpuInfo));
    std::string cpuType(brand.data());

    // Get architecture type (basic check based on intrinsics)
    std::string architecture;
    __cpuid(cpuInfo.data(), 1);
    if ((cpuInfo[3] & (1 << 23)) != 0) {  // Check if MMX is supported
        architecture = "x86";
    }
    if ((cpuInfo[3] & (1 << 30)) != 0) {  // Check if Intel 64-bit extensions are supported
        architecture = "x64";
    }

    return "CPU Type: " + cpuType + "\nArchitecture: " + architecture;
}

#else  // Assume Linux/Unix
#include <fstream>

std::string Utils::getCpuInfo() {
    std::ifstream cpuinfo("/proc/cpuinfo");
    std::string line;
    std::string cpuType;
    std::string architecture;

    while (std::getline(cpuinfo, line)) {
        if (line.find("model name") != std::string::npos) {
            cpuType = line.substr(line.find(":") + 2);
        }
        else if (line.find("architecture") != std::string::npos) {
            architecture = line.substr(line.find(":") + 2);
        }
    }

    if (architecture.empty()) { // Fallback for some Linux distributions
        std::ifstream archInfo("/proc/sys/kernel/osrelease");
        if (archInfo.good()) {
            architecture = "x86_64";  // Default if no architecture entry in /proc/cpuinfo
        }
    }

    return "CPU Type: " + cpuType + "\nArchitecture: " + architecture;
}
#endif

#ifdef QPP_OPENMP
#include <omp.h>
#endif
int Utils::saveResultsToJson(const std::map<std::string, double>& results, const std::string& filePath) {
    // Create a JSON object
    nlohmann::json jsonData;

    // Populate the JSON object with the results map
    for (const auto& [fileName, executionTime] : results) {
        jsonData[fileName] = executionTime;
    }

    jsonData["cpu"] = Utils::getCpuInfo();

#ifdef QPP_OPENMP
    jsonData["openmp"] = "1";

    int max_threads = omp_get_max_threads();
    jsonData["openmp_max_threads"] = max_threads;

    int num_procs = omp_get_num_procs();
    jsonData["openmp_num_procs"] = num_procs;
#else
    jsonData["openmp"] = "0";

#endif

#ifdef EIGEN_USE_BLAS
    jsonData["eigen_blas"] = "1";
#else
    jsonData["eigen_blas"] = "0";
#endif

#ifdef __CUDACC__
    jsonData["cuda"] = "1";
#else
    jsonData["cuda"] = "0";
#endif

    // Write the JSON data to a file
    std::ofstream file(filePath);
    if (file.is_open()) {
        file << jsonData.dump(4); // Pretty-print with 4-space indentation
        file.close();
    }
    else {
        return 1;
    }
    return 0;
}