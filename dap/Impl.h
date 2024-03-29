
#pragma once

#include "network.h"
#include "socket.h"

#include <mutex>
#include <thread>


class ServerImpl : public dap::net::Server {
    public:
        ServerImpl();
        ~ServerImpl();

        bool start(const char* host, int port,
            const OnConnect& onConnect) override;

        void stop() override;
        int removeDeadThreads();
        size_t getThreadsCount() const;

    private:
        inline bool isRunning() const { return !stopped; }
        void stopWithLock();

        std::mutex mutex;
        std::thread thread;
        std::unique_ptr<dap::Socket> socket;
        std::atomic<bool> stopped;
        OnError errorHandler;

        std::vector<std::shared_ptr<std::thread>> threads;
};


