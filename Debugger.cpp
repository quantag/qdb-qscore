/*
 * Copyright (c) 2024 Quantag IT Solutions GmbH
 *
 * This source code is licensed under the MIT license found in the
 * LICENSE file in the root directory of this source tree.
 */


#include "Debugger.h"

#include "Log.h"
#include "qvm/QppQVM.h"

Debugger::Debugger(const EventHandler& onEvent) : onEvent(onEvent), numSourceLines(0) {
    LOGI("Debugger created");

    qvm = new QppQVM();
}

Debugger::~Debugger() {
    LOGI("Debugger destroyed");
    delete qvm;
}

void Debugger::continueDebugger() {
      LOGI("***");
      std::unique_lock<std::mutex> lock(mutex);

      for (int64_t i = 0; i < numSourceLines; i++) {
            int64_t l = ((qvm->getCurrentLine() + i) % numSourceLines) + 1;
            if (breakpoints.count(l)) {
                  qvm->setCurrentLine( (int)l);
                  lock.unlock();
                  onEvent(EventEnum::BreakpointHit);
                  return;
            }
      }
}

int Debugger::launch(int isRun, const std::string& fileName, const std::string &sessionId, LaunchStatus& status) {
    LOGI("noDebug = %d, file = [%s] [%s]", isRun, fileName.c_str(), sessionId.c_str());

    int ret = ERR_OK;
    if (isRun) {
        ret = qvm->run(fileName, sessionId, status);
    }
    else {
        ret = qvm->debug(fileName, sessionId, status);
    }

    if (ret==ERR_OK) {
        this->numSourceLines = qvm->getSourceLines();
    }
    return ret;
}

void Debugger::pause() {
    LOGI("***");

    onEvent(EventEnum::Paused);
}

int64_t Debugger::currentLine() {
    LOGI("*** line = %d", qvm->getCurrentLine());

    std::unique_lock<std::mutex> lock(mutex);
    return qvm->getCurrentLine();
}

double Debugger::stepForward() {
      LOGI("*** line = %d, numSourceLines = %d", qvm->getCurrentLine(), numSourceLines);

      std::unique_lock<std::mutex> lock(mutex);
      auto executionTime = qvm->stepForward();

      lock.unlock();
      onEvent(EventEnum::Stepped);

      return executionTime;
}

void Debugger::clearBreakpoints() {
    LOGI("***");

    std::unique_lock<std::mutex> lock(mutex);
    this->breakpoints.clear();
}

void Debugger::addBreakpoint(int64_t l) {
    LOGI("*** line = %d", l);

    std::unique_lock<std::mutex> lock(mutex);
    this->breakpoints.emplace(l);
}

std::vector<complexNumber> Debugger::getQVMVariables() {
    return this->qvm->getCurrentState().states;
}

size_t Debugger::getQubitsCount() const {
    return qvm->getQubitsCount();
}