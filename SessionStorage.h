/*
 * Copyright (c) 2024 Quantag IT Solutions GmbH
 *
 * This source code is licensed under the MIT license found in the
 * LICENSE file in the root directory of this source tree.
 */

#pragma once

#include <string>
#include <mutex>
#include <map>
#include <set>
#include "dap/session.h"

class SessionStorage {
public:
	SessionStorage();
	~SessionStorage();

	static SessionStorage& getInstance() {
		static SessionStorage instance; // Static instance created only once
		return instance;
	}

	void add(const std::string& id, std::shared_ptr<dap::Session> session);
	void remove(const std::string& id);
	void removeLater(const std::string& id);

	dap::Session* findById(const std::string& id);
	size_t getSessionsCount();

	size_t cleanup();

private:
	std::mutex sessionMapMutex;

	std::unordered_map<std::string, std::shared_ptr<dap::Session>> sessionMap;
	std::set<std::string> removeLaterSet;
};