
#include "WSListener.h"

#include "WSSession.h"

#include "../Log.h"

WSListener::WSListener(net::io_context& ioc, tcp::endpoint endpoint) : ioc_(ioc), acceptor_(ioc), activeSession(NULL) {
    beast::error_code ec;

    // Open the acceptor
    acceptor_.open(endpoint.protocol(), ec);
    if (ec) {
        LOGE("Error open. %s", ec.message().c_str());
        return;
    }

    // Allow address reuse
    acceptor_.set_option(net::socket_base::reuse_address(true), ec);
    if (ec) {
        LOGE("Error set_option. %s", ec.message().c_str());
        return;
    }

    // Bind to the server address
    acceptor_.bind(endpoint, ec);
    if (ec) {
        LOGE("Error bind. %s", ec.message().c_str());
        return;
    }

    // Start listening for connections
    acceptor_.listen(net::socket_base::max_listen_connections, ec);
    if (ec) {
        LOGE("Error listen. %s", ec.message().c_str());
        return;
    }
}

void WSListener::run() {
    do_accept();
}

void WSListener::do_accept() {
    // The new connection gets its own strand
    acceptor_.async_accept(net::make_strand(ioc_),
        beast::bind_front_handler(&WSListener::on_accept, shared_from_this()));
}

void WSListener::on_accept(beast::error_code ec, tcp::socket socket) {
    if (ec) {
        LOGE("Error. %s", ec.message().c_str());
        this->activeSession = NULL;
    }
    else {
        // Create the session and run it
        auto s = std::make_shared<WSSession>(std::move(socket));
        this->activeSession = s.get();
        s->run();
    }

    // Accept another connection
    do_accept();
}