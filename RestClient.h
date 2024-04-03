#pragma once

#include "Typedefs.h"


class RestClient {
public:
    RestClient();
    RestClient(const char* _url);
    ~RestClient();

    std::string doPost(const std::string& jsonData);
    ScriptExecResult execCode(const std::string& code);

    void setEndpoint(const char* _url) {
        this->url = _url;
    }

private:
    static size_t writeCallback(void* contents, size_t size, size_t nmemb, std::string* output);

    std::string url;
    struct curl_slist* headers = NULL;
};

