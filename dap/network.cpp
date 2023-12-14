// Copyright 2019 Google LLC
//
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//     https://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.

#include "network.h"

#include "socket.h"

#include <atomic>
#include <mutex>
#include <string>
#include <thread>

#include "Impl.h"

#include "../Log.h"

namespace dap {
namespace net {

std::unique_ptr<Server> Server::create() {
    LOGI("");

    return std::unique_ptr<Server>(new ServerImpl());
}

/*std::shared_ptr<ReaderWriter> connect(const char* addr,
                                      int port,
                                      uint32_t timeoutMillis) {
    LOGI("DAP connect from %s:%d", addr, port);
    return Socket::connect(addr, std::to_string(port).c_str(), timeoutMillis);
}*/

}  // namespace net
}  // namespace dap
