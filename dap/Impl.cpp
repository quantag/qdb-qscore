
#include "Impl.h"

#include "../Log.h"

ServerImpl::ServerImpl() : stopped{ true } {
}

ServerImpl::~ServerImpl() {
	stop(); 
}

bool ServerImpl::start(const char* host, int port, const OnConnect& onConnect) {
    LOGI("");

    std::unique_lock<std::mutex> lock(mutex);
    stopWithLock();
    socket = std::unique_ptr<dap::Socket>(
        new dap::Socket(host, std::to_string(port).c_str()));

    if (!socket->isOpen()) {
        LOGE("Failed to open socket");
        return false;
    }

    stopped = false;
    thread = std::thread([=] {
        while (true) {
            if (auto rw = socket->accept()) {
                onConnect(rw);
                continue;
            }
            if (!stopped) {
                LOGE("Failed to accept connection");
            }
            break;
        };
        LOGI("Exited from endless loop");
    });

    return true;
}


void ServerImpl::stop() {
    LOGI("");
    std::unique_lock<std::mutex> lock(mutex);
    stopWithLock();
}

void ServerImpl::stopWithLock() {
    LOGI("");
    if (!stopped.exchange(true)) {
        socket->close();
        thread.join();
    }
}
