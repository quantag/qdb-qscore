#pragma once

#include <functional>
#include <mutex>
#include <unordered_set>


class WSServer;
class IQVM;

// Debugger holds the dummy debugger state and fires events to the EventHandler
// passed to the constructor.
class Debugger {
 public:
  enum class Event { BreakpointHit, Stepped, Paused };
  using EventHandler = std::function<void(Event)>;

  Debugger(const EventHandler&, WSServer*);
  ~Debugger();

  // run() instructs the debugger to continue execution.
  void continueDebugger();

  int launch(int isRun, const std::string& fileName);

  // pause() instructs the debugger to pause execution.
  void pause();

  // currentLine() returns the currently executing line number.
  int64_t currentLine();

  // stepForward() instructs the debugger to step forward one line.
  void stepForward();

  // clearBreakpoints() clears all set breakpoints.
  void clearBreakpoints();

  // addBreakpoint() sets a new breakpoint on the given line.
  void addBreakpoint(int64_t line);

  // Total number of newlines in source.
  int64_t numSourceLines;

 private:
  EventHandler onEvent;
  std::mutex mutex;
  int64_t line = 1;
  std::unordered_set<int64_t> breakpoints;

  IQVM* qvm;

};
