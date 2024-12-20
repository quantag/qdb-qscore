
/*
 * Copyright (c) 2024 Quantag IT Solutions GmbH
 *
 * This source code is licensed under the MIT license found in the
 * LICENSE file in the root directory of this source tree.
 */

#include "WSSession.h"
#include "../Log.h"
#include <boost/beast/http.hpp>
#include <streambuf>
#include <nlohmann/json.hpp>
#include "../SessionStorage.h"


using json = nlohmann::json;
namespace http = beast::http;           // from <boost/beast/http.hpp>


WSSession::WSSession(tcp::socket&& socket) : ws_(std::move(socket)) {
    LOGI("= New WS Connection from WebFront =");
    this->sessionId = "";
}

// Start the asynchronous operation
void WSSession::run() {
    // Set suggested timeout settings for the websocket
    ws_.set_option(
        websocket::stream_base::timeout::suggested(beast::role_type::server));

    // Set a decorator to change the Server of the handshake
    ws_.set_option(websocket::stream_base::decorator(
        [](websocket::response_type& res) {
            res.set(http::field::server,
            std::string(BOOST_BEAST_VERSION_STRING) +
            " websocket-server-async");
        }));

    // Accept the websocket handshake
    ws_.async_accept( beast::bind_front_handler( &WSSession::on_accept, shared_from_this()) );
}

void WSSession::send(const std::string& data) {
    LOGI("isOpen : %u, SEND> '%s'", ws_.is_open(), data.c_str());

    if (!ws_.is_open()) {
        LOGE("socket is not open..");
        return;
    }

    ws_.text(true);
    ws_.async_write(
        boost::asio::buffer(data.c_str(), data.size()),
        beast::bind_front_handler(&WSSession::on_write, shared_from_this()));
}

void WSSession::on_accept(beast::error_code ec) {
    if (ec) {
       LOGE("Error accept %s", ec.message().c_str());
       return;
    }

    // Read a message
    do_read();
}

void WSSession::do_read() {
    LOGI("");
    // Read a message into our buffer
    ws_.async_read( buffer_,
                    beast::bind_front_handler(
                        &WSSession::on_read,
                        shared_from_this()));
}

void WSSession::on_read(beast::error_code ec, std::size_t bytes_transferred) {
    LOGI("");
    boost::ignore_unused(bytes_transferred);

    // This indicates that the session was closed
    if (ec == websocket::error::closed)
        return;

    if (ec) {
        LOGE("Error read %s", ec.message().c_str());
    }

    // Echo the message
    ws_.text(ws_.got_text());
   
    std::string s(boost::asio::buffer_cast<const char*>(buffer_.data()), buffer_.size());
    LOGI("FRONT<< '%s'", s.c_str());

    try {
        json parsedJson = json::parse(s);
        if (parsedJson.contains("id"))
            this->setSessionId(parsedJson["id"]);

    } catch(...) {
        LOGE("Can not parse json");
    }
}

void WSSession::setSessionId(const std::string& id) {
    LOGI("%s", id.c_str());

    this->sessionId = id;

    SessionStorage& sessions = SessionStorage::getInstance();
    dap::Session *session = sessions.findById(id);
    if (session) {
        LOGI("** Session [%s] found !! in Session Storage", id.c_str());
        session->setWSSession(this);
    }
    else {
        LOGE("** Session with id [%s] not found in SessionStorage", id.c_str());
    }
}

void WSSession::on_write(beast::error_code ec, std::size_t bytes_transferred) {
    LOGI("");

    boost::ignore_unused(bytes_transferred);
    if (ec) {
        LOGE("Error write %s", ec.message().c_str());
        return;
    }

    // Clear the buffer
    buffer_.consume(buffer_.size());
}