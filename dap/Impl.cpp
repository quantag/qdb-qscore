
#include "Impl.h"
#include "../Log.h"

std::mutex threadsMutex;

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
 //               LOGI(">> new client connected. current threads count: %d", this->getThreadsCount());
 //               removeDeadThreads();
  //              LOGI(">> after removeDeadThreads() threads count: %d", this->getThreadsCount());

                std::thread sessionThread( onConnect, rw );
                sessionThread.detach();

             //   auto sessionThread = std::make_shared<std::thread>(onConnect, rw);
                // Lock the mutex before modifying the vector
             //   std::lock_guard<std::mutex> lock(threadsMutex);
             //   threads.push_back(sessionThread);

                LOGI("after onConnect");
                continue;
            }
            if (!stopped) {
                LOGE("Failed to accept connection");
            }
            break;
        };
        LOGI("Exited from server loop");
    });

    return true;
}

//int ServerImpl::removeDeadThreads() {
//    std::lock_guard<std::mutex> lock(threadsMutex);

    // Remove threads that have finished
//    threads.erase(std::remove_if(threads.begin(), threads.end(),
//        [](const std::shared_ptr<std::thread>& t) {
//            return !t->joinable();
//        }), threads.end());
//    return 0;
//}

//size_t ServerImpl::getThreadsCount() const {
//    std::lock_guard<std::mutex> lock(threadsMutex);

//    return this->threads.size();
//}

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

