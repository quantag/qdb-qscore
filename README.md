# qdb-qscore

## Prerequisites

```
sudo apt-get install git cmake build-essential libcurl4-gnutls-dev
```
## Build

Here is single line download-and-build command

```
git clone https://github.com/quantag/qdb-qscore.git && cd qdb-qscore && ./get_deps.sh && cd build && cmake .. && make
```

## Run

```
./QSCore
```

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
