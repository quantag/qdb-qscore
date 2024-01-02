// QSCore.cpp : This file contains the 'main' function. Program execution begins and ends there.
//


#include "dap/io.h"
#include "dap/network.h"
#include "dap/protocol.h"
#include "dap/session.h"

#include "Event.h"
#include "Debugger.h"

#include "ws/WSServer.h"

#include "Log.h"
#include "Utils.h"
#include "Typedefs.h"
#include "interfaces/iqvm.h"


#ifdef _MSC_VER
    #define OS_WINDOWS 1
#endif

#ifdef OS_WINDOWS
    #include <fcntl.h>  // _O_BINARY
    #include <io.h>     // _setmode
#endif              // OS_WINDOWS

#define DAP_SERVER_PORT     5555
#define WS_SERVER_PORT      5556

#define LOCALHOST   "127.0.0.1"



// sourceContent holds the synthetic file source.
constexpr char sourceContent[] = R"(// !
This is a synthetic source file provided by the DAP debugger.
You may also notice that the locals contains a single variable for the currently executing line number.)";



int main(int argc, char *argv[]) {
    LOG_INIT(2, "qs-core.log");
    WSServer wsock;

#ifdef OS_WINDOWS
	// Change stdin & stdout from text mode to binary mode.
	// This ensures sequences of \r\n are not changed to \n.
	_setmode(_fileno(stdin), _O_BINARY);
	_setmode(_fileno(stdout), _O_BINARY);
#endif  // OS_WINDOWS

	const dap::integer threadId = 100;
	const dap::integer frameId = 200;
	const dap::integer variablesReferenceId = 300;
	const dap::integer sourceReferenceId = 400;


    // Callback handler for a socket connection to the server
    auto onClientConnected =
        [&](const std::shared_ptr<dap::ReaderWriter>& socket) {
        // Signal events
        Event configured;
        Event terminate;

        LOGI("== DAP client CONNECTED ==");

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
        Debugger debugger(onDebuggerEvent, &wsock);

        // Set the session to close on invalid data. This ensures that data received over the network
        // receives a baseline level of validation before being processed.
        session->setOnInvalidData(dap::kClose);
        session->bind(socket);

  // The Initialize request is the first message sent from the client and
        // the response reports debugger capabilities.
        // https://microsoft.github.io/debug-adapter-protocol/specification#Requests_Initialize
        session->registerHandler([](const dap::InitializeRequest&) {
            LOGI("[InitializeRequest]");

            dap::InitializeResponse response;
            response.supportsConfigurationDoneRequest = true;
            response.supportsDisassembleRequest = true;
     
            return response;
        });

        // Handle errors reported by the Session. These errors include protocol
      // parsing errors and receiving messages with no handler.
        session->onError([&](const char* msg) {         
            LOGE("dap::Session error: %s", msg);          
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
            LOGI("[ThreadsRequest]");

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

                LOGI("[StackTraceRequest]");
                if (request.threadId != threadId) {
                    return dap::Error("Unknown threadId '%d'",
                        int(request.threadId));
                }

                dap::Source source;
                source.sourceReference = 0;

                source.path = session->currentSourceFilePath;
                source.name = Utils::getShortName(session->currentSourceFilePath);

                dap::StackFrame frame;
                frame.line = debugger.currentLine();
                frame.column = 1;
                frame.name = "QuantumDebugger";
                frame.id = frameId;
                frame.source = source;

                // this line makes 'Open Disassembly View" item active
                frame.instructionPointerReference = "0"; //TODO: put correct value. 

                dap::StackTraceResponse response;
                response.stackFrames.push_back(frame);
                return response;
            });


        session->registerHandler(
            [&](const dap::DisassemblyRequest& request)
            -> dap::ResponseOrError<dap::DisassemblyResponse> {

                LOGI("[DisassemblyRequest] %d", debugger.numSourceLines);
                dap::DisassemblyResponse response;

                if (debugger.getQVM()->isSourceCodeParsed()) {
                    int baseAddress = 100;
                    for(int i=0; i< debugger.getQVM()->getSourcePerLines().size(); i++) {
                        dap::DisassembledInstruction code;

                        code.address = Utils::intToString(baseAddress + i);
                        code.column = 1;
                        code.instruction = debugger.getQVM()->getSourcePerLines().at(i);

                        response.instructions.push_back(code);
                    }
                }

                return response;
            });

        // The Scopes request reports all the scopes of the given stack frame.
        // This example debugger only exposes a single 'Locals' scope for the
        // single frame.
        // https://microsoft.github.io/debug-adapter-protocol/specification#Requests_Scopes
        session->registerHandler(
            [&](const dap::ScopesRequest& request)
            -> dap::ResponseOrError<dap::ScopesResponse> {
                LOGI("[ScopesRequest]");

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
                LOGI("[VariablesRequest]");

                if (request.variablesReference != variablesReferenceId) {
                    return dap::Error("Unknown variablesReference '%d'",
                        int(request.variablesReference));
                }

             //   dap::Variable currentLineVar;
            //    currentLineVar.name = "currentLine";
            //    currentLineVar.value = std::to_string(debugger.currentLine());
             //   currentLineVar.type = "int";

                dap::VariablesResponse response;
            //    response.variables.push_back(currentLineVar);
                /*
                * add qubits here
                */
                std::vector<complexNumber> qubits = debugger.getQVMVariables();
                unsigned char idx = 0;
                for (complexNumber item : qubits) {
                    dap::Variable qubitVar;
                    qubitVar.name = "|" + Utils::toBinaryString(idx, debugger.getQubitsCount()) + ">";
                    qubitVar.value = Utils::complex2str(item);
                    qubitVar.type = "complex";
                    idx++;
                    response.variables.push_back(qubitVar);

                    LOGI( "adding variable %s", qubitVar.name.c_str() );
                }

                return response;
            });
        // The Pause request instructs the debugger to pause execution of one or
        // all threads.
        // https://microsoft.github.io/debug-adapter-protocol/specification#Requests_Pause
        session->registerHandler([&](const dap::PauseRequest&) {
            LOGI("[PauseRequest]");

            debugger.pause();
            return dap::PauseResponse();
            });

        // The Continue request instructs the debugger to resume execution of
        // one or all threads.
        // https://microsoft.github.io/debug-adapter-protocol/specification#Requests_Continue
        session->registerHandler([&](const dap::ContinueRequest&) {
            LOGI("[ContinueRequest]");

            debugger.continueDebugger();
            return dap::ContinueResponse();
            });

        // The Next request instructs the debugger to single line step for a
        // specific thread.
        // https://microsoft.github.io/debug-adapter-protocol/specification#Requests_Next
        session->registerHandler([&](const dap::NextRequest& req) {
            LOGI("*** [NextRequest] threadId=%d ***", req.threadId);

            debugger.stepForward();
            return dap::NextResponse();
            });
        // The StepIn request instructs the debugger to step-in for a specific
        // thread.
        // https://microsoft.github.io/debug-adapter-protocol/specification#Requests_StepIn
        session->registerHandler([&](const dap::StepInRequest&) {
            LOGI("[StepInRequest]");

            // Step-in treated as step-over as there's only one stack frame.
            debugger.stepForward();
            return dap::StepInResponse();
            });

        // The StepOut request instructs the debugger to step-out for a specific
        // thread.
        // https://microsoft.github.io/debug-adapter-protocol/specification#Requests_StepOut
        session->registerHandler([&](const dap::StepOutRequest&) {
            LOGI("[StepOutRequest]");

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
                LOGI("[SetBreakpointsRequest] v1 = %d v2 = %d", 
                    request.source.sourceReference.value(0), sourceReferenceId);

                auto breakpoints = request.breakpoints.value({});
                if (1) { //request.source.sourceReference.value(0) == sourceReferenceId) {
                    debugger.clearBreakpoints();
                    response.breakpoints.resize(breakpoints.size());
                    for (size_t i = 0; i < breakpoints.size(); i++) {
                        debugger.addBreakpoint(breakpoints[i].line);
                        response.breakpoints[i].verified =
                            breakpoints[i].line < debugger.numSourceLines;
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
                LOGI("[SetExceptionBreakpointsRequest]");

                return dap::SetExceptionBreakpointsResponse();
            });

        // The Source request retrieves the source code for a given source file.
              // This example debugger only exposes one synthetic source file.
              // https://microsoft.github.io/debug-adapter-protocol/specification#Requests_Source
        session->registerHandler(
            [&](const dap::SourceRequest& request)
            -> dap::ResponseOrError<dap::SourceResponse> {
                LOGI("[SourceRequest]");

                if (request.source.has_value()) {
                    LOGI("source = [%s]", request.source.value().path);
                }
                
                LOGI("sourceReference = [%d]", request.sourceReference);            
                if (request.sourceReference != sourceReferenceId) {
                    return dap::Error("Unknown source reference '%d'",
                        int(request.sourceReference));
                }

                dap::SourceResponse response;
                response.content = sourceContent; // TODO: remove?
                return response;
            });

        // The Launch request is made when the client instructs the debugger
              // adapter to start the debuggee. This request contains the launch
              // arguments. This example debugger does nothing with this request.
              // https://microsoft.github.io/debug-adapter-protocol/specification#Requests_Launch
        session->registerHandler([&](const dap::LaunchRequest& req) {
            LOGI(" ~ [LaunchRequest] [%s]", req.program.value().c_str());
           
            session->currentSourceFilePath = req.program.value();
            bool isRun = req.noDebug.has_value();

            int ok = debugger.launch(isRun, req.program.value());
            LOGI("QVM launch ret %d", ok);
            return dap::LaunchResponse();
        });


        // Handler for disconnect requests
        session->registerHandler([&](const dap::DisconnectRequest& request) {
            LOGI("[DisconnectRequest]");

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
            LOGI("[ConfigurationDoneRequest]");

            configured.fire();
            return dap::ConfigurationDoneResponse();
        });

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

    // Create the network server
    auto server = dap::net::Server::create();

    const char* dapHost = (argc > 1) ? argv[1] : LOCALHOST;
    server->start( dapHost, DAP_SERVER_PORT, onClientConnected);
    LOGI("DAP Server started on [%s:%d]", dapHost, DAP_SERVER_PORT);

    const char* wsHost = (argc > 2) ? argv[2] : LOCALHOST;
    LOGI("Starting WS Server on [%s:%d]", wsHost, WS_SERVER_PORT);
   
    wsock.start(wsHost, WS_SERVER_PORT);
    return 0;
}
