#include "RestClient.h"

#include "Log.h"
#include "Utils.h"

#include <curl/curl.h>
#include <nlohmann/json.hpp>

using json = nlohmann::json;

#define ENDPONT_URL "https://cryspprod3.quantag-it.com:444/api3/dec"

RestClient::RestClient() : url(ENDPONT_URL) {
        curl_global_init(CURL_GLOBAL_ALL);
        headers = curl_slist_append(headers, "Content-Type: application/json");
}

RestClient::~RestClient() {
        curl_global_cleanup();
}

std::string RestClient::doPost(const std::string& jsonData) {
        CURL* curl;
        CURLcode res;
        std::string response;

        curl = curl_easy_init();
        if (curl) {
            curl_easy_setopt(curl, CURLOPT_URL, url.c_str());
            curl_easy_setopt(curl, CURLOPT_POSTFIELDS, jsonData.c_str());
            curl_easy_setopt(curl, CURLOPT_POSTFIELDSIZE, (long)jsonData.length());
            curl_easy_setopt(curl, CURLOPT_HTTPHEADER, headers);
            curl_easy_setopt(curl, CURLOPT_WRITEFUNCTION, writeCallback);
            curl_easy_setopt(curl, CURLOPT_WRITEDATA, &response);

            curl_easy_setopt(curl, CURLOPT_SSL_VERIFYPEER, 0L);
            curl_easy_setopt(curl, CURLOPT_SSL_VERIFYHOST, 0L);

            res = curl_easy_perform(curl);
            if (res != CURLE_OK) {
                LOGE("curl_easy_perform() failed: %s", curl_easy_strerror(res) );
            }

            curl_easy_cleanup(curl);
        }

        return response;
}


size_t RestClient::writeCallback(void* contents, size_t size, size_t nmemb, std::string* output) {
        output->append((char*)contents, size * nmemb);
        return size * nmemb;
}

std::string RestClient::execPythonCode(const std::string& code) {
    LOGI("'%s'", code.c_str());

    std::string encoded = Utils::encode64(code);
    std::string req = "{\"src\":\"" + encoded + "\"}";
    LOGI("req: '%s'", req.c_str());

    std::string res = doPost(req);
    LOGI("response '%s'", res.c_str());

    try {
        json j = json::parse(res);
        return j["res"];
    }
    catch (...) {
        LOGE("Error during parsing JSON response: '%s'", res.c_str());
        return "";
    }
}
