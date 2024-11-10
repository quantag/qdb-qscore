/*
 * Copyright (c) 2024 Quantag IT Solutions GmbH
 *
 * This source code is licensed under the MIT license found in the
 * LICENSE file in the root directory of this source tree.
 */


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