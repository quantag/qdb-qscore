
#include "StdCapture.h"

#ifdef WIN32
     #include <io.h>
     #define dup _dup
     #define dup2 _dup2
     #define fileno _fileno
     #define close _close
     #define eof _eof
     #define read _read
#else
    #define eof feof
    #include <unistd.h>
#endif

#include <fcntl.h>
#include <stdio.h>

StdCapture::StdCapture() : m_capturing(false), m_init(false), m_oldStdErr(0) {

    m_pipe[READ] = 0;
    m_pipe[WRITE] = 0;
#ifdef WIN32
    if (_pipe(m_pipe, 65536, O_BINARY) == -1)
        return;
#else
    if (pipe(m_pipe) == -1)
        return;
#endif

    m_oldStdErr = dup(fileno(stderr));
    if ( m_oldStdErr == -1)
        return;

    m_init = true;
}

StdCapture::~StdCapture() {
    if (m_capturing) {
        EndCapture();
    }

    if (m_oldStdErr > 0)
        close(m_oldStdErr);
    if (m_pipe[READ] > 0)
        close(m_pipe[READ]);
    if (m_pipe[WRITE] > 0)
        close(m_pipe[WRITE]);

}

std::string StdCapture::GetCapture() const {
    std::string::size_type idx = m_captured.find_last_not_of("\r\n");
    if (idx == std::string::npos) {
        return m_captured;
    }
    else {
        return m_captured.substr(0, idx + 1);
    }
}

bool StdCapture::EndCapture() {
    if (!m_init)
        return false;
    if (!m_capturing)
        return false;

    fflush(stderr);

    dup2(m_oldStdErr, fileno(stderr));
    m_captured.clear();

    std::string buf;
    const int bufSize = 1024;
    buf.resize(bufSize);
    int bytesRead = 0;
    
#ifdef WIN32
    if (!eof(m_pipe[READ])) {
        bytesRead = read(m_pipe[READ], &(*buf.begin()), bufSize);
    }
#else
    bytesRead = read(m_pipe[READ], &(*buf.begin()), bufSize);
#endif

    while (bytesRead == bufSize) {
        m_captured += buf;
        bytesRead = 0;
#ifdef WIN32
        if (!eof(m_pipe[READ]))
#endif
        {
            bytesRead = read(m_pipe[READ], &(*buf.begin()), bufSize);
        }
    }
    if (bytesRead > 0) {
        buf.resize(bytesRead);
        m_captured += buf;
    }
    m_capturing = false;

    return true;
}

void StdCapture::BeginCapture() {
    if (!m_init)
        return;
    if (m_capturing)
        EndCapture();

    fflush(stderr);

    dup2(m_pipe[WRITE], fileno(stderr));
    m_capturing = true;
}