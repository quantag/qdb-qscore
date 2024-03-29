
#include "Debugger.h"

#include "Log.h"
#include "qvm/QppQVM.h"

Debugger::Debugger(const EventHandler& onEvent, WSServer* ws) : onEvent(onEvent), numSourceLines(0) {
    LOGI("Debugger created");

    qvm = new QppQVM(ws);
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

int Debugger::launch(int isRun, const std::string& fileName, const std::string &sessionId) {
    LOGI("noDebug = %d, file = [%s] [%s]", isRun, fileName.c_str(), sessionId.c_str());

    int ret = 0;
    if (isRun) {
        ret = qvm->run(fileName, sessionId);
    }
    else {
        ret = qvm->debug(fileName, sessionId);
    }

    if (ret==0) {
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

void Debugger::stepForward() {
      LOGI("*** line = %d, numSourceLines = %d", qvm->getCurrentLine(), numSourceLines);

      std::unique_lock<std::mutex> lock(mutex);
      qvm->stepForward();

      lock.unlock();
      onEvent(EventEnum::Stepped);
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