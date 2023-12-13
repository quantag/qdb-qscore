
#pragma once

#include <memory>

#include <boost/asio.hpp>
#include <boost/asio/ip/tcp.hpp>
#include <boost/beast.hpp>

class WSSession;

namespace net = boost::asio;            // from <boost/asio.hpp>
using tcp = boost::asio::ip::tcp;       // from <boost/asio/ip/tcp.hpp>
namespace beast = boost::beast;         // from <boost/beast.hpp>


// Accepts incoming connections and launches the sessions
class WSListener : public std::enable_shared_from_this<WSListener> {
    net::io_context& ioc_;
    tcp::acceptor acceptor_;

public:
    WSListener(net::io_context& ioc, tcp::endpoint endpoint);
    WSSession* activeSession;

    // Start accepting incoming connections
    void run();

private:
    void do_accept();
    void on_accept(beast::error_code ec, tcp::socket socket);
};

