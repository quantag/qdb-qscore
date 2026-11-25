/*
 * Copyright (c) 2024 Quantag IT Solutions GmbH
 *
 * This source code is licensed under the MIT license found in the
 * LICENSE file in the root directory of this source tree.
 */

// Progress messages in the Debug Console while a program is prepared for a debug or
// run session. For a Python program, preparing means running it on the Python executor
// (to get its circuit as OpenQASM), which takes as long as the program itself: seconds,
// or a minute and more for programs with optimization loops. Without messages the
// Debug Console stays empty all that time.
//
//   LaunchProgress progress(send, "main.py");   // "Preparing the program ..."
//   debugger->launch(...);                       // every 15 s: "Still preparing (15 s) ..."
//   progress.finish();                           // stops the messages, returns seconds

#pragma once

#include <chrono>
#include <condition_variable>
#include <cstdio>
#include <functional>
#include <mutex>
#include <string>
#include <thread>

class LaunchProgress {
public:
    using Send = std::function<void(const std::string&)>;

    LaunchProgress(Send send, const std::string& program,
                   std::chrono::milliseconds period = std::chrono::seconds(15))
        : send(std::move(send)), period(period), start(std::chrono::steady_clock::now()) {
        this->send(startMessage(program));
        worker = std::thread([this] { run(); });
    }

    ~LaunchProgress() { finish(); }

    LaunchProgress(const LaunchProgress&) = delete;
    LaunchProgress& operator=(const LaunchProgress&) = delete;

    // Stops the progress messages; returns the seconds since the start.
    double finish() {
        {
            std::lock_guard<std::mutex> lock(mutex);
            done = true;
        }
        cv.notify_all();
        if (worker.joinable()) {
            worker.join();
        }
        return elapsedSeconds();
    }

    double elapsedSeconds() const {
        return std::chrono::duration<double>(std::chrono::steady_clock::now() - start).count();
    }

    static bool isPython(const std::string& program) {
        return program.size() >= 3 && program.compare(program.size() - 3, 3, ".py") == 0;
    }

    static std::string startMessage(const std::string& program) {
        if (isPython(program)) {
            return "Preparing the program: running it on the Python executor to get its circuit. "
                   "Programs with optimization loops can take a minute or more.";
        }
        return "Preparing the program ...";
    }

    static std::string seconds(double s) {
        char text[32];
        snprintf(text, sizeof(text), "%.1f s", s);
        return text;
    }

private:
    void run() {
        std::unique_lock<std::mutex> lock(mutex);
        while (!cv.wait_for(lock, period, [this] { return done; })) {
            const long elapsed = (long)(elapsedSeconds() + 0.5);
            lock.unlock();
            send("Still preparing the program (" + std::to_string(elapsed) + " s) ...");
            lock.lock();
        }
    }

    Send send;
    std::chrono::milliseconds period;
    std::chrono::steady_clock::time_point start;
    std::mutex mutex;
    std::condition_variable cv;
    bool done = false;
    std::thread worker;
};
