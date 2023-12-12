
#pragma once

#include "network.h"
#include "socket.h"

#include <mutex>
#include <thread>


class Impl : public dap::net::Server {
    public:
        Impl();
        ~Impl();

        bool start(const char* host, int port,
            const OnConnect& onConnect,
            const OnError& onError) override;

        void stop() override;

    private:
        inline bool isRunning() const { return !stopped; }
        void stopWithLock();

        std::mutex mutex;
        std::thread thread;
        std::unique_ptr<dap::Socket> socket;
        std::atomic<bool> stopped;
        OnError errorHandler;
};


