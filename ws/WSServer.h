
/*
 * Copyright (c) 2024 Quantag IT Solutions GmbH
 *
 * This source code is licensed under the MIT license found in the
 * LICENSE file in the root directory of this source tree.
 */

#pragma once
#include <string>

class WSListener;

class WSServer {
public:
	WSServer();
	~WSServer();
		
	void	start(const char *host, int port);
	int		send(const std::string& data);

private:
	WSListener* list;
};