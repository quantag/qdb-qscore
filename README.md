This is QSCore repository (Quantag Studio Core). Cross platform unit which combines quantum virtual machine - currently supported [QPP](https://github.com/softwareQinc/qpp) and implementation of Microsoft [Debugger Adapter Protocol](https://microsoft.github.io/debug-adapter-protocol) distributed under MIT license.

It allows to debug quantum circuits from any IDE which supports [DAP](https://microsoft.github.io/debug-adapter-protocol/implementors/tools/) written
in OpenQASM or Python (currently supported [Qiskit](https://www.ibm.com/quantum/qiskit) and [PyTKET](https://docs.quantinuum.com/tket/) frameworks)

VS Code Extension which works with QSCode can be downloaded directly from VS Code [here](https://marketplace.visualstudio.com/items?itemName=QuantagITSolutionsGmbH.openqasm-debug)

# qdb-qscore

## Prerequisites

```
sudo apt-get install git cmake build-essential libcurl4-gnutls-dev libomp-dev libblas-dev
```
## Build

Here is single line download-and-build command

```
git clone https://github.com/quantag/qdb-qscore.git && cd qdb-qscore && cd build && cmake .. && make
```

## Run

To start QSCore in default server mode just execute it without command line arguments
```
./QSCore
```

To measure performace execute it with 'test':

```
./QSCore test [<folder with .qasm files>] [<output file name>]
```
It will excute .qasm files from specified folder one by one and write executions times to JSON file with CPU information. 
If data folder not specified '../test/qasm' will be used. If output file name not specified 'results.json' used.

## Configuration (Optionally)

Optionally QSCore can be configured by creation of __QSCore.ini__ file in same folder with binary. 
It is text file with 'key'='value' parameters per line like java .properties files. 
Following parameters are supported:

__render.circuit=0|1 (default is 1)__

Should OpenQASM circuit be rendered to image during parsing or not.

__demo.file__

Location of demo .qasm file to use if provided file is not found

__source.folder (default /var/dap)__

Where to search for source files on server 


## Other microservices

Quantum Debugger backend consist of several microservices, not only this one. 

- DAP files - microservice to upload files to server [dap-files](https://github.com/quantag/dap-files)

- qdb-decom - python scripts executor [qdb-decom](scripts/qdb-decom)
