
#include "Impl.h"

#include "../Log.h"

Impl::Impl() : stopped{ true } {
}

Impl::~Impl() { 
	stop(); 
}

bool Impl::start(const char* host, int port, const OnConnect& onConnect) {

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


void Impl::stop() {
    LOGI("");
    std::unique_lock<std::mutex> lock(mutex);
    stopWithLock();
}

void Impl::stopWithLock() {
    LOGI("");
    if (!stopped.exchange(true)) {
        socket->close();
        thread.join();
    }
}
