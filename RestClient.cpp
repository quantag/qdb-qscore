#include "RestClient.h"

#include "Log.h"
#include "Utils.h"

#include <curl/curl.h>
#include <nlohmann/json.hpp>

using json = nlohmann::json;

RestClient::RestClient() : url(PYTHON_EXECUTER_ENDPONT_URL) {
    curl_global_init(CURL_GLOBAL_ALL);
    headers = curl_slist_append(headers, "Content-Type: application/json");
}

RestClient::RestClient(const char* _url) : url(_url) {
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

ScriptExecResult RestClient::execCode(const std::string& code) {
    LOGD("'%s'", code.c_str());

    std::string encoded = Utils::encode64(code);
    std::string req = "{\"src\":\"" + encoded + "\"}";
    LOGD("req: '%s'", req.c_str());

    std::string res = doPost(req);
    LOGD("response '%s'", res.c_str());
    ScriptExecResult result;

    try {
        json j = json::parse(res);
        result.status = j["status"];
        if (result.status != 0) {
            result.err = j["err"];
            LOGE("Remote script execution failed [%s]", result.err.c_str());
        }
        else {
            std::string encodedRes = j["res"];
            result.res = Utils::decode64(encodedRes);
        }
        return result;
    }
    catch (std::exception& e) {
        LOGE("Error during parsing JSON response: '%s'", res.c_str());
        result.err = 3;
        result.err = e.what();
        return result;
    }
}

