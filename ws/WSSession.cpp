
#include "WSSession.h"

#include "../Log.h"
#include <boost/beast/http.hpp>

namespace http = beast::http;           // from <boost/beast/http.hpp>


WSSession::WSSession(tcp::socket&& socket) : ws_(std::move(socket)), ignoreReadAfterWrite(0) {
    LOGI("= New WS Connection from [%s] =", socket.remote_endpoint().address().to_v4().to_string().c_str());
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
//    LOGI("SEND> '%s'", data.c_str());

    ws_.text(true);
    ignoreReadAfterWrite = 1;
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
    // Read a message into our buffer
    ws_.async_read( buffer_,
                    beast::bind_front_handler(
                        &WSSession::on_read,
                        shared_from_this()));
}

void WSSession::on_read(beast::error_code ec, std::size_t bytes_transferred) {
    boost::ignore_unused(bytes_transferred);

    // This indicates that the session was closed
    if (ec == websocket::error::closed)
        return;

    if (ec) {
        LOGE("Error read %s", ec.message().c_str());
    }

    // Echo the message
    ws_.text(ws_.got_text());
    ws_.async_write( buffer_.data(), beast::bind_front_handler( &WSSession::on_write, shared_from_this()) );
}

void WSSession::on_write(beast::error_code ec, std::size_t bytes_transferred) {
    boost::ignore_unused(bytes_transferred);
    if (ec) {
        LOGE("Error write %s", ec.message().c_str());
        return;
    }

    // Clear the buffer
    buffer_.consume(buffer_.size());

    if (ignoreReadAfterWrite) {
        ignoreReadAfterWrite = 0;
    }
    else {
        // Do another read
        do_read();
    }
}