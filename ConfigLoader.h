/*
 * Copyright (c) 2024 Quantag IT Solutions GmbH
 *
 * This source code is licensed under the MIT license found in the
 * LICENSE file in the root directory of this source tree.
 */

#pragma once
#include <cstring>   // for strcmp
#include <iostream>
#include <fstream>
#include <sstream>
#include <string>
#include <map>

#define RENDER_CIRCUIT_KEY          "render.circuit"
#define DEMO_FILE_KEY               "demo.file"
#define SOURCE_FOLDER_KEY           "source.folder"
#define LOG_LEVEL_KEY               "log.level"
#define QVM_TYPE_KEY                "qvm.type"
#define CUDAQ_SRV_KEY               "cudaq.srv"


#define PYTHON_EXEC_ENDPOINT_KEY    "python.exec.endpoint"


#define MODE_KEY                "mode"
#define FILE_KEY                "file"
#define TEST_FOLDER_KEY         "test.folder"
#define OUTPUT_FILE_KEY         "output.file"
#define DAP_HOST_KEY            "dap.host"
#define WS_HOST_KEY             "ws.host"
#define NODENAME_KEY            "node"

 // defaults
#define DEMO_FILE_DEFAULT       "./file1.qasm"
#define SOURCE_FOLDER_DEFAULT   "/var/dap/"
#define CUDAQ_SRV_DEFAULT       "https://cloud.quantag-it.com/api1/run"

#define MODE_DEFAULT            "server"
#define FILE_DEFAULT            ""
#define TEST_FOLDER_DEFAULT     "../test/qasm"
#define OUTPUT_FILE_DEFAULT     "results.json"
#define DAP_HOST_DEFAULT        "127.0.0.1"
#define WS_HOST_DEFAULT         "127.0.0.1"
#define NODENAME_DEFAULT        "node"



class ConfigLoader {
public:
    // Load the properties file and parse it
    bool load(const std::string& filename) {
        std::ifstream file(filename);
        if (!file.is_open()) {
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

            if (std::getline(lineStream, key, '=') && std::getline(lineStream, value)) {
                key = trim(key);
                value = trim(value);
                properties_[key] = value;
            }
        }

        file.close();
        return true;
    }

    // Helper: get value with default
    std::string getOrDefault(const std::string& key, const std::string& def) const {
        auto it = properties_.find(key);
        if (it != properties_.end()) {
            std::string value = trim(it->second);
            return value;
        }
        return def;
    }

    // Helpers for overriding from CLI
    void set(const std::string& key, const std::string& value) {
        properties_[key] = value;
    }

    // Accessors
    bool isRenderCircuit() {
        std::string val = getOrDefault(RENDER_CIRCUIT_KEY, "1");
        return !(val == "0" || val == "false");
    }

    int getLogLevel() {
        return std::stoi(getOrDefault(LOG_LEVEL_KEY, "2"));
    }

    std::string getSourceFolder() {
        return getOrDefault(SOURCE_FOLDER_KEY, SOURCE_FOLDER_DEFAULT);
    }

    std::string getPythonExecutorEndpoint() {
        return getOrDefault(PYTHON_EXEC_ENDPOINT_KEY, PYTHON_EXECUTER_ENDPONT_URL);
    }

    std::string getCudaQSrvEndpoint() {
        return getOrDefault(CUDAQ_SRV_KEY, CUDAQ_SRV_DEFAULT);
    }

    std::string getNodeName() {
        return getOrDefault(NODENAME_KEY, NODENAME_DEFAULT);
    }

    std::string getDemoFile() {
        return getOrDefault(DEMO_FILE_KEY, DEMO_FILE_DEFAULT);
    }

    std::string getQvmType() {
        return getOrDefault(QVM_TYPE_KEY, "qpp");
    }

    // New getters for CLI-style options
    std::string getMode() {
        return getOrDefault(MODE_KEY, MODE_DEFAULT);
    }

    std::string getFile() {
        return getOrDefault(FILE_KEY, FILE_DEFAULT);
    }

    std::string getTestFolder() {
        return getOrDefault(TEST_FOLDER_KEY, TEST_FOLDER_DEFAULT);
    }

    std::string getOutputFile() {
        return getOrDefault(OUTPUT_FILE_KEY, OUTPUT_FILE_DEFAULT);
    }

    std::string getDapHost() {
        return getOrDefault(DAP_HOST_KEY, DAP_HOST_DEFAULT);
    }

    std::string getWsHost() {
        return getOrDefault(WS_HOST_KEY, WS_HOST_DEFAULT);
    }

private:
    std::map<std::string, std::string> properties_;

    // Trim whitespace
    static std::string trim(const std::string& str) {
        size_t first = str.find_first_not_of(" \t\r\n");
        if (first == std::string::npos) return "";
        size_t last = str.find_last_not_of(" \t\r\n");
        return str.substr(first, last - first + 1);
    }
};
