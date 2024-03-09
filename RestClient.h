#pragma once

#include <string>

class RestClient {
public:
public:
    RestClient();
    ~RestClient();

    std::string doPost(const std::string& jsonData);
    std::string execPythonCode(const std::string& code);

private:
    static size_t writeCallback(void* contents, size_t size, size_t nmemb, std::string* output);

    const std::string url;
    struct curl_slist* headers = NULL;
};