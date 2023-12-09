
#include "WSServer.h"

#include <boost/beast/core.hpp>
#include <boost/beast/websocket.hpp>
#include <boost/asio/strand.hpp>


#include <algorithm>
#include <cstdlib>
#include <functional>
#include <iostream>
#include <memory>
#include <string>
#include <thread>
#include <vector>
#include <future>

#include "../Log.h"

#include "WSListener.h"
#include "WSSession.h"

namespace net = boost::asio;            // from <boost/asio.hpp>
using tcp = boost::asio::ip::tcp;       // from <boost/asio/ip/tcp.hpp>


WSServer::WSServer() : list(NULL) 
{
}

WSServer::~WSServer() 
{
}

void WSServer::start(const char* host, int _port) 
{
    auto const address = net::ip::make_address( (host!=NULL) ? host : "127.0.0.1");
    auto const port = static_cast<unsigned short>( _port );
    auto const threads = std::max<int>(1,  1);

    // The io_context is required for all I/O
    net::io_context ioc{ threads };

    // Create and launch a listening port
    auto liste = std::make_shared<WSListener>(ioc, tcp::endpoint{ address, port });
    this->list = liste.get();
    liste->run();

    // Run the I/O service on the requested number of threads
    std::vector<std::thread> v;
    v.reserve(threads - 1);
    for (auto i = threads - 1; i > 0; --i)
        v.emplace_back(
                [&ioc]
                {
                    ioc.run();
                });

    ioc.run();
}

int WSServer::send(const std::string& data) 
{
    if (!this->list) return 1;
    if (!this->list->activeSession) return 2;

    try 
    {
        this->list->activeSession->send(data);
    }
    catch (...) 
    {
        return 3;
    }

    return 0;
}