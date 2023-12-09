
#include "Debugger.h"



Debugger::Debugger(const EventHandler& onEvent) : onEvent(onEvent) {}

void Debugger::run() {
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

void Debugger::pause() {
  onEvent(Event::Paused);
}

int64_t Debugger::currentLine() {
  std::unique_lock<std::mutex> lock(mutex);
  return line;
}

void Debugger::stepForward() {
  std::unique_lock<std::mutex> lock(mutex);
  line = (line % numSourceLines) + 1;
  lock.unlock();
  onEvent(Event::Stepped);
}

void Debugger::clearBreakpoints() {
  std::unique_lock<std::mutex> lock(mutex);
  this->breakpoints.clear();
}

void Debugger::addBreakpoint(int64_t l) {
  std::unique_lock<std::mutex> lock(mutex);
  this->breakpoints.emplace(l);
}
