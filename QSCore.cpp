// QSCore.cpp : This file contains the 'main' function. Program execution begins and ends there.
//

#include <iostream>

#include "dap/io.h"
#include "dap/network.h"
#include "dap/protocol.h"
#include "dap/session.h"

#include "Event.h"
#include "Debugger.h"

#include <conio.h>

#ifdef _MSC_VER
#define OS_WINDOWS 1
#endif

// Uncomment the line below and change <path-to-log-file> to a file path to
// write all DAP communications to the given path.
//
#define LOG_TO_FILE		"dap.log"

#ifdef OS_WINDOWS
#include <fcntl.h>  // _O_BINARY
#include <io.h>     // _setmode
#endif              // OS_WINDOWS

// sourceContent holds the synthetic file source.
constexpr char sourceContent[] = R"(// Hello Debugger!
This is a synthetic source file provided by the DAP debugger.
You can set breakpoints, and single line step.
You may also notice that the locals contains a single variable for the currently executing line number.)";



int main(int argc, char *argv[]) {

#ifdef OS_WINDOWS
	// Change stdin & stdout from text mode to binary mode.
	// This ensures sequences of \r\n are not changed to \n.
	_setmode(_fileno(stdin), _O_BINARY);
	_setmode(_fileno(stdout), _O_BINARY);
#endif  // OS_WINDOWS

	std::shared_ptr<dap::Writer> log;

#ifdef LOG_TO_FILE
	log = dap::file(LOG_TO_FILE);
#endif

	constexpr int kPort = 5555;

	const dap::integer threadId = 100;
	const dap::integer frameId = 200;
	const dap::integer variablesReferenceId = 300;
	const dap::integer sourceReferenceId = 400;

	// Signal events
	Event configured;
	Event terminate;

    // Callback handler for a socket connection to the server
    auto onClientConnected =
        [&](const std::shared_ptr<dap::ReaderWriter>& socket) {
        auto session = dap::Session::create();

        // Event handlers from the Debugger.
        auto onDebuggerEvent = [&](Debugger::Event onEvent) {
            switch (onEvent) {
            case Debugger::Event::Stepped: {
                // The debugger has single-line stepped. Inform the client.
                dap::StoppedEvent event;
                event.reason = "step";
                event.threadId = threadId;
                session->send(event);
                break;
            }
            case Debugger::Event::BreakpointHit: {
                // The debugger has hit a breakpoint. Inform the client.
                dap::StoppedEvent event;
                event.reason = "breakpoint";
                event.threadId = threadId;
                session->send(event);
                break;
            }
            case Debugger::Event::Paused: {
                // The debugger has been suspended. Inform the client.
                dap::StoppedEvent event;
                event.reason = "pause";
                event.threadId = threadId;
                session->send(event);
                break;
            }
            }
            };

        // Construct the debugger.
        Debugger debugger(onDebuggerEvent);

        // Set the session to close on invalid data. This ensures that data received over the network
        // receives a baseline level of validation before being processed.
        session->setOnInvalidData(dap::kClose);
        session->bind(socket);




        // 000000000000000000000000



  // The Initialize request is the first message sent from the client and
        // the response reports debugger capabilities.
        // https://microsoft.github.io/debug-adapter-protocol/specification#Requests_Initialize
        session->registerHandler([](const dap::InitializeRequest&) {
            std::cout << "[InitializeRequest]" << std::endl;

            dap::InitializeResponse response;
            response.supportsConfigurationDoneRequest = true;
            return response;
            });

        // Handle errors reported by the Session. These errors include protocol
      // parsing errors and receiving messages with no handler.
        session->onError([&](const char* msg) {
            if (log) {
                dap::writef(log, "dap::Session error: %s\n", msg);
                log->close();
            }
            terminate.fire();
            });

        // When the Initialize response has been sent, we need to send the
        // initialized event. We use the registerSentHandler() to ensure the
        // event is sent *after* the initialize response.
        // https://microsoft.github.io/debug-adapter-protocol/specification#Events_Initialized
        session->registerSentHandler(
            [&](const dap::ResponseOrError<dap::InitializeResponse>&) {
                session->send(dap::InitializedEvent());
            });


        // The Threads request queries the debugger's list of active threads.
              // This example debugger only exposes a single thread.
              // https://microsoft.github.io/debug-adapter-protocol/specification#Requests_Threads
        session->registerHandler([&](const dap::ThreadsRequest&) {
            std::cout << "[ThreadsRequest]" << std::endl;

            dap::ThreadsResponse response;
            dap::Thread thread;
            thread.id = threadId;
            thread.name = "TheThread";
            response.threads.push_back(thread);
            return response;
            });

        // The StackTrace request reports the stack frames (call stack) for a
              // given thread. This example debugger only exposes a single stack frame
              // for the single thread.
              // https://microsoft.github.io/debug-adapter-protocol/specification#Requests_StackTrace
        session->registerHandler(
            [&](const dap::StackTraceRequest& request)
            -> dap::ResponseOrError<dap::StackTraceResponse> {

                std::cout << "[StackTraceRequest]" << std::endl;

                if (request.threadId != threadId) {
                    return dap::Error("Unknown threadId '%d'",
                        int(request.threadId));
                }

                dap::Source source;
                source.sourceReference = 0;
                //sourceReferenceId;
                source.path = "c:\\work\\gitquantag\\qasm-adapter-vscode\\sampleWorkspace\\qft.qasm";
                source.name = "qft.qasm";

                dap::StackFrame frame;
                frame.line = debugger.currentLine();
                frame.column = 1;
                frame.name = "HelloDebugger";
                frame.id = frameId;
                frame.source = source;

                dap::StackTraceResponse response;
                response.stackFrames.push_back(frame);
                return response;
            });
        // The Scopes request reports all the scopes of the given stack frame.
        // This example debugger only exposes a single 'Locals' scope for the
        // single frame.
        // https://microsoft.github.io/debug-adapter-protocol/specification#Requests_Scopes
        session->registerHandler(
            [&](const dap::ScopesRequest& request)
            -> dap::ResponseOrError<dap::ScopesResponse> {
                std::cout << "[ScopesRequest]" << std::endl;

                if (request.frameId != frameId) {
                    return dap::Error("Unknown frameId '%d'", int(request.frameId));
                }

                dap::Scope scope;
                scope.name = "Locals";
                scope.presentationHint = "locals";
                scope.variablesReference = variablesReferenceId;

                dap::ScopesResponse response;
                response.scopes.push_back(scope);
                return response;
            });

        // The Variables request reports all the variables for the given scope.
              // This example debugger only exposes a single 'currentLine' variable
              // for the single 'Locals' scope.
              // https://microsoft.github.io/debug-adapter-protocol/specification#Requests_Variables
        session->registerHandler(
            [&](const dap::VariablesRequest& request)
            -> dap::ResponseOrError<dap::VariablesResponse> {
                std::cout << "[VariablesRequest]" << std::endl;

                if (request.variablesReference != variablesReferenceId) {
                    return dap::Error("Unknown variablesReference '%d'",
                        int(request.variablesReference));
                }

                dap::Variable currentLineVar;
                currentLineVar.name = "currentLine";
                currentLineVar.value = std::to_string(debugger.currentLine());
                currentLineVar.type = "int";

                dap::VariablesResponse response;
                response.variables.push_back(currentLineVar);
                return response;
            });
        // The Pause request instructs the debugger to pause execution of one or
        // all threads.
        // https://microsoft.github.io/debug-adapter-protocol/specification#Requests_Pause
        session->registerHandler([&](const dap::PauseRequest&) {
            std::cout << "[PauseRequest]" << std::endl;

            debugger.pause();
            return dap::PauseResponse();
            });

        // The Continue request instructs the debugger to resume execution of
        // one or all threads.
        // https://microsoft.github.io/debug-adapter-protocol/specification#Requests_Continue
        session->registerHandler([&](const dap::ContinueRequest&) {
            std::cout << "[ContinueRequest]" << std::endl;

            debugger.run();
            return dap::ContinueResponse();
            });

        // The Next request instructs the debugger to single line step for a
        // specific thread.
        // https://microsoft.github.io/debug-adapter-protocol/specification#Requests_Next
        session->registerHandler([&](const dap::NextRequest&) {
            std::cout << "[NextRequest]" << std::endl;

            debugger.stepForward();
            return dap::NextResponse();
            });
        // The StepIn request instructs the debugger to step-in for a specific
        // thread.
        // https://microsoft.github.io/debug-adapter-protocol/specification#Requests_StepIn
        session->registerHandler([&](const dap::StepInRequest&) {
            std::cout << "[StepInRequest]" << std::endl;

            // Step-in treated as step-over as there's only one stack frame.
            debugger.stepForward();
            return dap::StepInResponse();
            });

        // The StepOut request instructs the debugger to step-out for a specific
        // thread.
        // https://microsoft.github.io/debug-adapter-protocol/specification#Requests_StepOut
        session->registerHandler([&](const dap::StepOutRequest&) {
            std::cout << "[StepOutRequest]" << std::endl;

            // Step-out is not supported as there's only one stack frame.
            return dap::StepOutResponse();
            });

        // The SetBreakpoints request instructs the debugger to clear and set a
              // number of line breakpoints for a specific source file. This example
              // debugger only exposes a single source file.
              // https://microsoft.github.io/debug-adapter-protocol/specification#Requests_SetBreakpoints
        session->registerHandler(
            [&](const dap::SetBreakpointsRequest& request) {
                dap::SetBreakpointsResponse response;

                std::cout << "[SetBreakpointsRequest]" << std::endl;

                auto breakpoints = request.breakpoints.value({});
                if (request.source.sourceReference.value(0) ==
                    sourceReferenceId) {
                    debugger.clearBreakpoints();
                    response.breakpoints.resize(breakpoints.size());
                    for (size_t i = 0; i < breakpoints.size(); i++) {
                        debugger.addBreakpoint(breakpoints[i].line);
                        response.breakpoints[i].verified =
                            breakpoints[i].line < numSourceLines;
                    }
                }
                else {
                    response.breakpoints.resize(breakpoints.size());
                }

                return response;
            });

        // The SetExceptionBreakpoints request configures the debugger's
              // handling of thrown exceptions. This example debugger does not use any
              // exceptions, so this is a no-op.
              // https://microsoft.github.io/debug-adapter-protocol/specification#Requests_SetExceptionBreakpoints
        session->registerHandler(
            [&](const dap::SetExceptionBreakpointsRequest&) {
                std::cout << "[SetExceptionBreakpointsRequest]" << std::endl;

                return dap::SetExceptionBreakpointsResponse();
            });

        // The Source request retrieves the source code for a given source file.
              // This example debugger only exposes one synthetic source file.
              // https://microsoft.github.io/debug-adapter-protocol/specification#Requests_Source
        session->registerHandler(
            [&](const dap::SourceRequest& request)
            -> dap::ResponseOrError<dap::SourceResponse> {
                std::cout << "[SourceRequest]" << std::endl;

                if (request.sourceReference != sourceReferenceId) {
                    return dap::Error("Unknown source reference '%d'",
                        int(request.sourceReference));
                }


                dap::SourceResponse response;
                response.content = sourceContent;
                return response;
            });

        // The Launch request is made when the client instructs the debugger
              // adapter to start the debuggee. This request contains the launch
              // arguments. This example debugger does nothing with this request.
              // https://microsoft.github.io/debug-adapter-protocol/specification#Requests_Launch
        session->registerHandler([&](const dap::LaunchRequest&) {
            std::cout << "[LaunchRequest]" << std::endl;
            return dap::LaunchResponse();
            });


        // Handler for disconnect requests
        session->registerHandler([&](const dap::DisconnectRequest& request) {
            std::cout << "[DisconnectRequest]" << std::endl;

            if (request.terminateDebuggee.value(false)) {
                terminate.fire();
            }
            return dap::DisconnectResponse();
            });

        // The ConfigurationDone request is made by the client once all
              // configuration requests have been made. This example debugger uses
              // this request to 'start' the debugger.
              // https://microsoft.github.io/debug-adapter-protocol/specification#Requests_ConfigurationDone
        session->registerHandler([&](const dap::ConfigurationDoneRequest&) {
            std::cout << "[ConfigurationDoneRequest]" << std::endl;

            configured.fire();
            return dap::ConfigurationDoneResponse();
            });



        /*
                // Signal used to terminate the server session when a DisconnectRequest
                // is made by the client.
                bool terminate = false;
                std::condition_variable cv;
                std::mutex mutex;  // guards 'terminate'

                // Wait for the client to disconnect (or reach a 5 second timeout)
                // before releasing the session and disconnecting the socket to the
                // client.
                std::unique_lock<std::mutex> lock(mutex);
                cv.wait_for(lock, std::chrono::seconds(5), [&] { return terminate; });
                printf("Server closing connection\n");
                */

                // Wait for the ConfigurationDone request to be made.
        configured.wait();

        // Broadcast the existance of the single thread to the client.
        dap::ThreadEvent threadStartedEvent;
        threadStartedEvent.reason = "started";
        threadStartedEvent.threadId = threadId;
        session->send(threadStartedEvent);

        // Start the debugger in a paused state.
        // This sends a stopped event to the client.
        debugger.pause();

        // Block until we receive a 'terminateDebuggee' request or encounter a
        // session error.
        terminate.wait();
        };

    // Error handler
    auto onError = [&](const char* msg) { printf("Server error: %s\n", msg); };

    // Create the network server
    auto server = dap::net::Server::create();
    // Start listening on kPort.
    // onClientConnected will be called when a client wants to connect.
    // onError will be called on any connection errors.
    server->start(kPort, onClientConnected, onError);


    _getch();
    return 0;


}
