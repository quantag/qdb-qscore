
#include "Impl.h"

#include "../Log.h"

ServerImpl::ServerImpl() : stopped{ true } {
}

ServerImpl::~ServerImpl() {
	stop(); 
}

bool ServerImpl::start(const char* host, int port, const OnConnect& onConnect) {
    LOGI("port %d", port);

    std::unique_lock<std::mutex> lock(mutex);
    stopWithLock();
    socket = std::unique_ptr<dap::Socket>( new dap::Socket(host, std::to_string(port).c_str()) );

    if (!socket->isOpen()) {
        LOGE("Failed to open socket");
        return false;
    }
    LOGI("Socket successfully opened");

    stopped = false;
    thread = std::thread([=] {
        while (true) {
            if (auto rw = socket->accept()) {
                
                std::thread sessionThread( onConnect, rw );
                sessionThread.detach();
                LOGI("after onConnect");
                continue;
            }
            LOGI(" p1 ");
            if (!stopped) {
                LOGE("Failed to accept connection");
            }
            break;
        };
        LOGI("Exited from server loop");
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
