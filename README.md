This is QSCore repository (Quantag Studio Core). Cross platform unit which combines quantum virtual machine - currently supported QPP (https://github.com/softwareQinc/qpp) and implementation of Microsoft Debugger Adapter Protocol (https://microsoft.github.io/debug-adapter-protocol) distributed under MIT license.

It allows to debug quantum circuits from any IDE which supports DAP (https://microsoft.github.io/debug-adapter-protocol/implementors/tools/) written
in OpenQASM or Python (currently supported Qiskit (https://www.ibm.com/quantum/qiskit) and PyTKET (https://docs.quantinuum.com/tket/) frameworks)

VS Code Extension which works with QSCode can be downloaded directly from VS Code here:
https://marketplace.visualstudio.com/items?itemName=QuantagITSolutionsGmbH.openqasm-debug

# qdb-qscore

## Prerequisites

### Linux
```
sudo apt-get install git cmake build-essential libcurl4-gnutls-dev libomp-dev libblas-dev
```

### Windows
- Install Visual Studio 2022 with "Desktop development with C++" workload  
- Ensure cmake and git are available (from https://cmake.org/download/ and https://git-scm.com/download/win)  
- PowerShell 5.0 or newer (comes with Windows 10 and 11 by default)  

## Build

### Linux (single line)
```
git clone git@github.com:quantag/qdb-qscore.git && cd qdb-qscore && ./get_deps.sh && cd build && cmake .. && make
```

### Windows
Open PowerShell and run:
```
git clone https://github.com/quantag/qdb-qscore.git
cd qdb-qscore
.\get_deps.ps1
```

This will download and unpack all dependencies into the "third_party" folder.  
Then, open "qdb-qscore.sln" in Visual Studio 2022 and build the solution (Debug or Release).

## Run

### Linux
To start QSCore in default server mode just execute it without command line arguments:
```
./QSCore
```

To measure performance execute it with "test":
```
./QSCore test [<folder with .qasm files>] [<output file name>]
```
It will execute .qasm files from the specified folder one by one and write execution times to a JSON file with CPU information.  
If the data folder is not specified, "../test/qasm" will be used.  
If the output file name is not specified, "results.json" will be used.

### Windows
After building in Visual Studio, the QSCore.exe binary will be available under:
```
qdb-qscore\x64\Release\QSCore.exe
```

Run it from x64\Release or x64\Debug depending on your configuration:
```
.\QSCore.exe
.\QSCore.exe test ..\test\qasm results.json
```

## Configuration (Optional)

QSCore can be configured by creating a "QSCore.ini" file in the same folder as the binary.  
It is a text file with "key=value" parameters per line (similar to Java .properties files).  
Supported parameters:

- render.circuit=0|1 (default 1)  
  Should OpenQASM circuit be rendered to image during parsing or not.

- demo.file  
  Location of demo .qasm file to use if provided file is not found.

- source.folder (default /var/dap)  
  Where to search for source files on server.

## Other microservices

Quantum Debugger backend consists of several microservices, not only this one:

- dap-files (https://github.com/quantag/dap-files) - microservice to upload files to server
- qdb-decom (scripts/qdb-decom) - Python scripts executor
