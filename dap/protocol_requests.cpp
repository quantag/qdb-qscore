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

// Generated with protocol_gen.go -- do not edit this file.
//   go run scripts/protocol_gen/protocol_gen.go
//
// DAP version 1.59.0

#include "protocol.h"

namespace dap {

DAP_IMPLEMENT_STRUCT_TYPEINFO(AttachRequest,
                              "attach",
                              DAP_FIELD(restart, "__restart"));

DAP_IMPLEMENT_STRUCT_TYPEINFO(BreakpointLocationsRequest,
                              "breakpointLocations",
                              DAP_FIELD(column, "column"),
                              DAP_FIELD(endColumn, "endColumn"),
                              DAP_FIELD(endLine, "endLine"),
                              DAP_FIELD(line, "line"),
                              DAP_FIELD(source, "source"));

DAP_IMPLEMENT_STRUCT_TYPEINFO(CancelRequest,
                              "cancel",
                              DAP_FIELD(progressId, "progressId"),
                              DAP_FIELD(requestId, "requestId"));

DAP_IMPLEMENT_STRUCT_TYPEINFO(CompletionsRequest,
                              "completions",
                              DAP_FIELD(column, "column"),
                              DAP_FIELD(frameId, "frameId"),
                              DAP_FIELD(line, "line"),
                              DAP_FIELD(text, "text"));

DAP_IMPLEMENT_STRUCT_TYPEINFO(ConfigurationDoneRequest, "configurationDone");

DAP_IMPLEMENT_STRUCT_TYPEINFO(ContinueRequest,
                              "continue",
                              DAP_FIELD(singleThread, "singleThread"),
                              DAP_FIELD(threadId, "threadId"));

DAP_IMPLEMENT_STRUCT_TYPEINFO(DataBreakpointInfoRequest,
                              "dataBreakpointInfo",
                              DAP_FIELD(frameId, "frameId"),
                              DAP_FIELD(name, "name"),
                              DAP_FIELD(variablesReference,
                                        "variablesReference"));

DAP_IMPLEMENT_STRUCT_TYPEINFO(DisassembleRequest,
                              "disassemble",
                              DAP_FIELD(instructionCount, "instructionCount"),
                              DAP_FIELD(instructionOffset, "instructionOffset"),
                              DAP_FIELD(memoryReference, "memoryReference"),
                              DAP_FIELD(offset, "offset"),
                              DAP_FIELD(resolveSymbols, "resolveSymbols"));

DAP_IMPLEMENT_STRUCT_TYPEINFO(DisconnectRequest,
                              "disconnect",
                              DAP_FIELD(restart, "restart"),
                              DAP_FIELD(suspendDebuggee, "suspendDebuggee"),
                              DAP_FIELD(terminateDebuggee,
                                        "terminateDebuggee"));

DAP_IMPLEMENT_STRUCT_TYPEINFO(EvaluateRequest,
                              "evaluate",
                              DAP_FIELD(context, "context"),
                              DAP_FIELD(expression, "expression"),
                              DAP_FIELD(format, "format"),
                              DAP_FIELD(frameId, "frameId"));

DAP_IMPLEMENT_STRUCT_TYPEINFO(ExceptionInfoRequest,
                              "exceptionInfo",
                              DAP_FIELD(threadId, "threadId"));

DAP_IMPLEMENT_STRUCT_TYPEINFO(GotoRequest,
                              "goto",
                              DAP_FIELD(targetId, "targetId"),
                              DAP_FIELD(threadId, "threadId"));

DAP_IMPLEMENT_STRUCT_TYPEINFO(GotoTargetsRequest,
                              "gotoTargets",
                              DAP_FIELD(column, "column"),
                              DAP_FIELD(line, "line"),
                              DAP_FIELD(source, "source"));

DAP_IMPLEMENT_STRUCT_TYPEINFO(
    InitializeRequest,
    "initialize",
    DAP_FIELD(adapterID, "adapterID"),
    DAP_FIELD(clientID, "clientID"),
    DAP_FIELD(clientName, "clientName"),
    DAP_FIELD(columnsStartAt1, "columnsStartAt1"),
    DAP_FIELD(linesStartAt1, "linesStartAt1"),
    DAP_FIELD(locale, "locale"),
    DAP_FIELD(pathFormat, "pathFormat"),
    DAP_FIELD(supportsArgsCanBeInterpretedByShell,
              "supportsArgsCanBeInterpretedByShell"),
    DAP_FIELD(supportsInvalidatedEvent, "supportsInvalidatedEvent"),
    DAP_FIELD(supportsMemoryEvent, "supportsMemoryEvent"),
    DAP_FIELD(supportsMemoryReferences, "supportsMemoryReferences"),
    DAP_FIELD(supportsProgressReporting, "supportsProgressReporting"),
    DAP_FIELD(supportsRunInTerminalRequest, "supportsRunInTerminalRequest"),
    DAP_FIELD(supportsStartDebuggingRequest, "supportsStartDebuggingRequest"),
    DAP_FIELD(supportsVariablePaging, "supportsVariablePaging"),
    DAP_FIELD(supportsVariableType, "supportsVariableType"));

DAP_IMPLEMENT_STRUCT_TYPEINFO(LaunchRequest,
                              "launch",
                              DAP_FIELD(restart, "__restart"),
                              DAP_FIELD(program, "program"),
                              DAP_FIELD(sessionId, "__sessionId"),
                              DAP_FIELD(noDebug, "noDebug"));

DAP_IMPLEMENT_STRUCT_TYPEINFO(LoadedSourcesRequest, "loadedSources");

DAP_IMPLEMENT_STRUCT_TYPEINFO(ModulesRequest,
                              "modules",
                              DAP_FIELD(moduleCount, "moduleCount"),
                              DAP_FIELD(startModule, "startModule"));

DAP_IMPLEMENT_STRUCT_TYPEINFO(NextRequest,
                              "next",
                              DAP_FIELD(granularity, "granularity"),
                              DAP_FIELD(singleThread, "singleThread"),
                              DAP_FIELD(threadId, "threadId"));

DAP_IMPLEMENT_STRUCT_TYPEINFO(PauseRequest,
                              "pause",
                              DAP_FIELD(threadId, "threadId"));

DAP_IMPLEMENT_STRUCT_TYPEINFO(ReadMemoryRequest,
                              "readMemory",
                              DAP_FIELD(count, "count"),
                              DAP_FIELD(memoryReference, "memoryReference"),
                              DAP_FIELD(offset, "offset"));

DAP_IMPLEMENT_STRUCT_TYPEINFO(RestartFrameRequest,
                              "restartFrame",
                              DAP_FIELD(frameId, "frameId"));

DAP_IMPLEMENT_STRUCT_TYPEINFO(RestartRequest,
                              "restart",
                              DAP_FIELD(arguments, "arguments"));

DAP_IMPLEMENT_STRUCT_TYPEINFO(ReverseContinueRequest,
                              "reverseContinue",
                              DAP_FIELD(singleThread, "singleThread"),
                              DAP_FIELD(threadId, "threadId"));

DAP_IMPLEMENT_STRUCT_TYPEINFO(RunInTerminalRequest,
                              "runInTerminal",
                              DAP_FIELD(args, "args"),
                              DAP_FIELD(argsCanBeInterpretedByShell,
                                        "argsCanBeInterpretedByShell"),
                              DAP_FIELD(cwd, "cwd"),
                              DAP_FIELD(env, "env"),
                              DAP_FIELD(kind, "kind"),
                              DAP_FIELD(title, "title"));

DAP_IMPLEMENT_STRUCT_TYPEINFO(ScopesRequest,
                              "scopes",
                              DAP_FIELD(frameId, "frameId"));

DAP_IMPLEMENT_STRUCT_TYPEINFO(SetBreakpointsRequest,
                              "setBreakpoints",
                              DAP_FIELD(breakpoints, "breakpoints"),
                              DAP_FIELD(lines, "lines"),
                              DAP_FIELD(source, "source"),
                              DAP_FIELD(sourceModified, "sourceModified"));

DAP_IMPLEMENT_STRUCT_TYPEINFO(SetDataBreakpointsRequest,
                              "setDataBreakpoints",
                              DAP_FIELD(breakpoints, "breakpoints"));

DAP_IMPLEMENT_STRUCT_TYPEINFO(SetExceptionBreakpointsRequest,
                              "setExceptionBreakpoints",
                              DAP_FIELD(exceptionOptions, "exceptionOptions"),
                              DAP_FIELD(filterOptions, "filterOptions"),
                              DAP_FIELD(filters, "filters"));

DAP_IMPLEMENT_STRUCT_TYPEINFO(SetExpressionRequest,
                              "setExpression",
                              DAP_FIELD(expression, "expression"),
                              DAP_FIELD(format, "format"),
                              DAP_FIELD(frameId, "frameId"),
                              DAP_FIELD(value, "value"));

DAP_IMPLEMENT_STRUCT_TYPEINFO(SetFunctionBreakpointsRequest,
                              "setFunctionBreakpoints",
                              DAP_FIELD(breakpoints, "breakpoints"));

DAP_IMPLEMENT_STRUCT_TYPEINFO(SetInstructionBreakpointsRequest,
                              "setInstructionBreakpoints",
                              DAP_FIELD(breakpoints, "breakpoints"));

DAP_IMPLEMENT_STRUCT_TYPEINFO(SetVariableRequest,
                              "setVariable",
                              DAP_FIELD(format, "format"),
                              DAP_FIELD(name, "name"),
                              DAP_FIELD(value, "value"),
                              DAP_FIELD(variablesReference,
                                        "variablesReference"));

DAP_IMPLEMENT_STRUCT_TYPEINFO(SourceRequest,
                              "source",
                              DAP_FIELD(source, "source"),
                              DAP_FIELD(sourceReference, "sourceReference"));

DAP_IMPLEMENT_STRUCT_TYPEINFO(StackTraceRequest,
                              "stackTrace",
                              DAP_FIELD(format, "format"),
                              DAP_FIELD(levels, "levels"),
                              DAP_FIELD(startFrame, "startFrame"),
                              DAP_FIELD(threadId, "threadId"));

DAP_IMPLEMENT_STRUCT_TYPEINFO(DisassemblyRequest,
    "disassemble",
    DAP_FIELD(memoryReference, "memoryReference"),
    DAP_FIELD(offset, "offset"),
    DAP_FIELD(instructionOffset, "instructionOffset"),
    DAP_FIELD(resolveSymbols, "resolveSymbols"),
    DAP_FIELD(instructionCount, "instructionCount"));



DAP_IMPLEMENT_STRUCT_TYPEINFO(StartDebuggingRequest,
                              "startDebugging",
                              DAP_FIELD(configuration, "configuration"),
                              DAP_FIELD(request, "request"));

DAP_IMPLEMENT_STRUCT_TYPEINFO(StepBackRequest,
                              "stepBack",
                              DAP_FIELD(granularity, "granularity"),
                              DAP_FIELD(singleThread, "singleThread"),
                              DAP_FIELD(threadId, "threadId"));

DAP_IMPLEMENT_STRUCT_TYPEINFO(StepInRequest,
                              "stepIn",
                              DAP_FIELD(granularity, "granularity"),
                              DAP_FIELD(singleThread, "singleThread"),
                              DAP_FIELD(targetId, "targetId"),
                              DAP_FIELD(threadId, "threadId"));

DAP_IMPLEMENT_STRUCT_TYPEINFO(StepInTargetsRequest,
                              "stepInTargets",
                              DAP_FIELD(frameId, "frameId"));

DAP_IMPLEMENT_STRUCT_TYPEINFO(StepOutRequest,
                              "stepOut",
                              DAP_FIELD(granularity, "granularity"),
                              DAP_FIELD(singleThread, "singleThread"),
                              DAP_FIELD(threadId, "threadId"));

DAP_IMPLEMENT_STRUCT_TYPEINFO(TerminateRequest,
                              "terminate",
                              DAP_FIELD(restart, "restart"));

DAP_IMPLEMENT_STRUCT_TYPEINFO(TerminateThreadsRequest,
                              "terminateThreads",
                              DAP_FIELD(threadIds, "threadIds"));

DAP_IMPLEMENT_STRUCT_TYPEINFO(ThreadsRequest, "threads");

DAP_IMPLEMENT_STRUCT_TYPEINFO(VariablesRequest,
                              "variables",
                              DAP_FIELD(count, "count"),
                              DAP_FIELD(filter, "filter"),
                              DAP_FIELD(format, "format"),
                              DAP_FIELD(start, "start"),
                              DAP_FIELD(variablesReference,
                                        "variablesReference"));

DAP_IMPLEMENT_STRUCT_TYPEINFO(WriteMemoryRequest,
                              "writeMemory",
                              DAP_FIELD(allowPartial, "allowPartial"),
                              DAP_FIELD(data, "data"),
                              DAP_FIELD(memoryReference, "memoryReference"),
                              DAP_FIELD(offset, "offset"));

}  // namespace dap
