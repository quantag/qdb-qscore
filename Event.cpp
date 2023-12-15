
#include "Event.h"

#include "Log.h"

void Event::wait() {
	LOGI("%x", this);

	std::unique_lock<std::mutex> lock(mutex);
	cv.wait(lock, [&] { return fired; });
}

void Event::fire() {
	LOGI("%x", this);

	std::unique_lock<std::mutex> lock(mutex);
	fired = true;
	cv.notify_all();
}