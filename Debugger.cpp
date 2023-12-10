
#include "Debugger.h"

#include "Log.h"
#include "qvm/QppQVM.h"

Debugger::Debugger(const EventHandler& onEvent, WSServer* ws) : onEvent(onEvent), numSourceLines(0) {
    qvm = new QppQVM(ws);
}

Debugger::~Debugger() {
    delete qvm;
}

void Debugger::continueDebugger() {
      LOGI("***");
      std::unique_lock<std::mutex> lock(mutex);

      for (int64_t i = 0; i < numSourceLines; i++) {
            int64_t l = ((line + i) % numSourceLines) + 1;
            if (breakpoints.count(l)) {
                  line = l;
                  lock.unlock();
                  onEvent(Event::BreakpointHit);
                  return;
            }
      }
}

int Debugger::launch(int isRun, const std::string& fileName) {
    LOGI("noDebug = %d, file = [%s]", isRun, fileName.c_str());

    int ret = 0;
    if (isRun) {
        ret = qvm->run(fileName);
    }
    else {
        ret = qvm->debug(fileName);
    }

    if (ret==0) {
        this->numSourceLines = qvm->getSourceLines();
    }
    return ret;
}


void Debugger::pause() {
    LOGI("***");

    onEvent(Event::Paused);
}

int64_t Debugger::currentLine() {
    LOGI("*** line = %d", line);

    std::unique_lock<std::mutex> lock(mutex);
    return line;
}

void Debugger::stepForward() {
      LOGI("***");

      std::unique_lock<std::mutex> lock(mutex);

      if(numSourceLines>0)
        line = (line % numSourceLines) + 1;

      qvm->stepForward();

      lock.unlock();
      onEvent(Event::Stepped);
}

void Debugger::clearBreakpoints() {
    LOGI("***");

    std::unique_lock<std::mutex> lock(mutex);
    this->breakpoints.clear();
}

void Debugger::addBreakpoint(int64_t l) {
    LOGI("***");

    std::unique_lock<std::mutex> lock(mutex);
    this->breakpoints.emplace(l);
}
