#pragma once

#include <mutex>
#include <unordered_set>

#include "Typedefs.h"
#include "interfaces/iqvm.h"


class Debugger {
 public:
	Debugger(const EventHandler&);
	~Debugger();

	// run() instructs the debugger to continue execution.
	void continueDebugger();

	int launch(int isRun, const std::string& fileName, const std::string& sessionId, LaunchStatus& status);

	// pause() instructs the debugger to pause execution.
	void pause();

	// currentLine() returns the currently executing line number.
	int64_t currentLine();

	// stepForward() instructs the debugger to step forward one line.
	double stepForward();

	// clearBreakpoints() clears all set breakpoints.
	void clearBreakpoints();

	// addBreakpoint() sets a new breakpoint on the given line.
	void addBreakpoint(int64_t line);

	// Total number of newlines in source.
	int64_t numSourceLines;

	std::vector<complexNumber> getQVMVariables();
	virtual size_t getQubitsCount() const;

  IQVM* getQVM() {
	  return qvm;
  }

  std::string getLastErrorMessage() {
	  return qvm->_errorMessage;
  }

 private:
	EventHandler onEvent;
	std::mutex mutex;
	std::unordered_set<int64_t> breakpoints;

	IQVM* qvm;
};
