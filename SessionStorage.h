#pragma once

#include <string>
#include <mutex>
#include <map>
#include "dap/session.h"

class SessionStorage {
public:
	SessionStorage();
	~SessionStorage();

	void add(const std::string& id, std::shared_ptr<dap::Session> session);
	void remove(const std::string& id);
	dap::Session* findById(const std::string& id);
	size_t getSessionsCount();

private:
	std::mutex sessionMapMutex;
	std::unordered_map<std::string, std::shared_ptr<dap::Session>> sessionMap;
};