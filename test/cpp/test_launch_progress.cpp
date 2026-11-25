// Tests of LaunchProgress.h (progress messages while a program is prepared).
// Build and run: g++ -std=c++17 -I. test/cpp/test_launch_progress.cpp -lpthread -o /tmp/tlp && /tmp/tlp
#include "LaunchProgress.h"
#include <cassert>
#include <cstdio>
#include <vector>

int main() {
    using namespace std::chrono;
    std::vector<std::string> sent;
    std::mutex m;
    auto send = [&](const std::string& s) { std::lock_guard<std::mutex> l(m); sent.push_back(s); };

    {   // start message, periodic messages, nothing after finish
        LaunchProgress p(send, "/var/dap/s/main.py", milliseconds(100));
        std::this_thread::sleep_for(milliseconds(350));
        double s = p.finish();
        assert(s >= 0.3 && s < 1.0);
        size_t n = sent.size();
        std::this_thread::sleep_for(milliseconds(250));
        assert(sent.size() == n);
        assert(n == 4);  // start + 3 x "Still preparing"
        assert(sent[0].find("Python executor") != std::string::npos);
        assert(sent[1].rfind("Still preparing the program (", 0) == 0);
    }
    {   // fast launch: only the start message; finish twice and destructor are safe
        sent.clear();
        LaunchProgress p(send, "circuit.qasm", milliseconds(100));
        p.finish();
        p.finish();
        assert(sent.size() == 1 && sent[0] == "Preparing the program ...");
    }
    {   // destructor alone stops the thread
        sent.clear();
        { LaunchProgress p(send, "a.py", seconds(60)); }
        assert(sent.size() == 1);
    }
    assert(LaunchProgress::seconds(17.24) == "17.2 s");
    assert(LaunchProgress::isPython("x.py") && !LaunchProgress::isPython("x.qasm") && !LaunchProgress::isPython("py"));
    printf("LaunchProgress: all tests passed\n");
    return 0;
}
