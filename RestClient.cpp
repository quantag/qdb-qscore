/*
 * Copyright (c) 2024 Quantag IT Solutions GmbH
 *
 * This source code is licensed under the MIT license found in the
 * LICENSE file in the root directory of this source tree.
 */

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

std::string RestClient::doPost(const std::string& jsonData, std::string* error) {
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

            // Without limits a hanging executor blocks the debug launch forever
            curl_easy_setopt(curl, CURLOPT_CONNECTTIMEOUT, connectTimeoutSec);
            curl_easy_setopt(curl, CURLOPT_TIMEOUT, timeoutSec);
            curl_easy_setopt(curl, CURLOPT_NOSIGNAL, 1L);  // timeouts in multi-threaded programs

            res = curl_easy_perform(curl);
            if (res != CURLE_OK) {
                LOGE("curl_easy_perform() failed: %s [%s]", curl_easy_strerror(res), url.c_str());
                if (error) {
                    *error = std::string("Python executor ") + url + " did not respond: " + curl_easy_strerror(res);
                    if (res == CURLE_OPERATION_TIMEDOUT) {
                        *error += " (limit " + std::to_string(timeoutSec) + " s)";
                    }
                }
                response.clear();
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
    LOGD("'%s' endpoint = [%s]", code.c_str(), url.c_str());

    std::string encoded = Utils::encode64(code);
    std::string req = "{\"src\":\"" + encoded + "\"}";
    LOGD("req: '%s'", req.c_str());

    std::string error;
    std::string res = doPost(req, &error);
    LOGD("response '%s'", res.c_str());
    return parseExecResponse(res, error);
}

// Response of the Python executor: {"status": 0, "res": <base64>} or {"status": N, "err": ...}
ScriptExecResult RestClient::parseExecResponse(const std::string& res, const std::string& error) {
    ScriptExecResult result;
    result.status = 0;

    if (!error.empty()) {
        result.status = 2;
        result.err = error;
        LOGE("%s", error.c_str());
        return result;
    }

    try {
        json j = json::parse(res);
        result.status = j["status"];
        if (result.status != 0) {
            result.err = j.value("err", std::string("Python executor returned status ") + std::to_string(result.status));
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
        result.status = 3;
        result.err = std::string("Invalid response from the Python executor ") + url + ": " + e.what();
        return result;
    }
}


ScriptExecResult RestClient::execCode(const std::string& code, const std::string& env) {
    LOGI("'%s' endpoint = [%s] venv=[%s]", code.c_str(), url.c_str(), env.c_str());

    std::string encoded = Utils::encode64(code);

    json j;
    j["src"] = encoded;
    if (!env.empty()) {
        j["env"] = env;
    }
    std::string req = j.dump();
    LOGD("req: '%s'", req.c_str());

    std::string error;
    std::string res = doPost(req, &error);
    LOGD("response '%s'", res.c_str());
    return parseExecResponse(res, error);
}