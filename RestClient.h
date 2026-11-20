/*
 * Copyright (c) 2024 Quantag IT Solutions GmbH
 *
 * This source code is licensed under the MIT license found in the
 * LICENSE file in the root directory of this source tree.
 */

#pragma once

#include "Typedefs.h"

class RestClient {
public:
    RestClient();
    RestClient(const char* _url);
    ~RestClient();

    // POST jsonData; on a transport error (no connection, timeout) returns "" and,
    // when error is given, sets it to a message naming the endpoint
    std::string doPost(const std::string& jsonData, std::string* error = nullptr);
    ScriptExecResult execCode(const std::string& code);
    ScriptExecResult execCode(const std::string& code, const std::string& env);

    void setEndpoint(const char* _url) {
        this->url = _url;
    }

    // Seconds a request to the Python executor may take (the executor itself stops a
    // script after 120 s by default); 0 = no limit
    void setTimeout(long seconds) {
        this->timeoutSec = seconds;
    }

private:
    static size_t writeCallback(void* contents, size_t size, size_t nmemb, std::string* output);

    std::string url;
    struct curl_slist* headers = NULL;
    long connectTimeoutSec = 15;
    long timeoutSec = 180;

    ScriptExecResult parseExecResponse(const std::string& res, const std::string& error);
};

