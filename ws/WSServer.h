#pragma once

#include <string>

class WSListener;

class WSServer 
{
public:
	WSServer();
	~WSServer();
		
	void	start(const char *host, int port);
	int		send(const std::string& data);

private:
	WSListener* list;
};