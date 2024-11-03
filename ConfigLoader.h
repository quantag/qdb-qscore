#pragma once

#include <iostream>
#include <fstream>
#include <sstream>
#include <string>
#include <map>

#define RENDER_CIRCUIT_KEY      "render.circuit"
#define DEMO_FILE_KEY           "demo.file"
#define SOURCE_FOLDER_KEY       "source.folder"

#define DEMO_FILE		"/home/qbit/qasm/file1.qasm"
#define SOURCE_FOLDER	"/var/dap/"

class ConfigLoader {
public:
    // Load the properties file and parse it
    bool load(const std::string& filename) {
        std::ifstream file(filename);
        if (!file.is_open()) {
            // LOGI( "Failed to open config file: %s", filename);
            return false;
        }

        std::string line;
        while (std::getline(file, line)) {
            // Ignore empty lines and comments
            if (line.empty() || line[0] == '#') {
                continue;
            }

            std::istringstream lineStream(line);
            std::string key, value;

            // Parse key-value pair
            if (std::getline(lineStream, key, '=') && std::getline(lineStream, value)) {
                // Trim whitespace from key and value
                key = trim(key);
                value = trim(value);
                properties_[key] = value;
            }
        }

        file.close();
        return true;
    }

    bool isRenderCircuit() {
        std::string val = getValue(RENDER_CIRCUIT_KEY);
        if (!val.empty()) {
            if (!strcmp(val.c_str(), "0"))
                return false;
        }
        return true;
    }

    std::string getSourceFolder() {
        std::string val = getValue(SOURCE_FOLDER_KEY);
        if (!val.empty()) {
            return val;
        }
        return SOURCE_FOLDER;
    }

    std::string getDemoFile() {
        std::string val = getValue(DEMO_FILE);
        if (!val.empty()) {
            return val;
        }
        return DEMO_FILE;
    }

    // Get the value associated with a given key
    std::string getValue(const std::string& key) const {
        auto it = properties_.find(key);
        if (it != properties_.end()) {
            return it->second;
        }
        return ""; // Return an empty string if the key is not found
    }

private:
    std::map<std::string, std::string> properties_;

    // Helper function to trim whitespace from start and end of a string
    std::string trim(const std::string& str) const {
        size_t first = str.find_first_not_of(" \t");
        if (first == std::string::npos) return "";
        size_t last = str.find_last_not_of(" \t");
        return str.substr(first, last - first + 1);
    }
};
