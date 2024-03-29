
#include "SessionStorage.h"

#include "Log.h"


SessionStorage::SessionStorage() {

}

SessionStorage::~SessionStorage() {

}

void SessionStorage::add(const std::string& id, std::shared_ptr<dap::Session> session) {
    LOGI("-->> add [%s]", id.c_str());

    if (id.empty()) {
        return;
    }

    std::lock_guard<std::mutex> lock(sessionMapMutex);
    sessionMap[id] = session;
}

void SessionStorage::remove(const std::string& id) {
    LOGI("-->> remove [%s]", id.c_str());

    std::lock_guard<std::mutex> lock(sessionMapMutex);
    sessionMap.erase(id);
}

dap::Session* SessionStorage::findById(const std::string& id) {
    std::lock_guard<std::mutex> lock(sessionMapMutex);

    auto it = sessionMap.find(id);
    if (it != sessionMap.end()) {
        return it->second.get(); // Return raw pointer
    }
    return nullptr; // Session not found
}

size_t SessionStorage::getSessionsCount() {
    std::lock_guard<std::mutex> lock(sessionMapMutex);

    return sessionMap.size();
}

void SessionStorage::removeLater(const std::string& id) {
    LOGI("removeLater [%s]", id.c_str());

    this->removeLaterSet.insert(id);
}

size_t SessionStorage::cleanup() {
    LOGI("Cleanup. RemoveLater size: %u", this->removeLaterSet.size());
    // Iterate over removeLaterSet and remove sessions from sessionMap
    size_t removedCount = 0;
    for (const auto& id : removeLaterSet) {
        auto it = sessionMap.find(id);
        if (it != sessionMap.end()) {
            sessionMap.erase(it);
            ++removedCount;
        }
    }

    // Clear removeLaterSet after removing sessions
    removeLaterSet.clear();

    return removedCount;
}