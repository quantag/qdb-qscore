#pragma once

#include <condition_variable>
#include <mutex>

// Event provides a basic wait and signal synchronization primitive.
class Event {
public:
	// wait() blocks until the event is fired.
	void wait();

	// fire() sets signals the event, and unblocks any calls to wait().
	void fire();

private:
	std::mutex mutex;
	std::condition_variable cv;
	bool fired = false;
};