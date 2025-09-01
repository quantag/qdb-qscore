// Log.cpp
#include "Log.h"
#include <cstdio>
#include <cstdarg>
#include <ctime>
#include <chrono>
#ifdef _WIN32
#include <windows.h>
#endif


Logger Logger::logger;

Logger::Logger() : _mode(LO_CONSOLE), _level(Log::eInfo), _file(nullptr) {}

Logger::~Logger() {
    if (_file) fclose(_file);
}

void Logger::init(int level, const std::string& filename) {
    std::lock_guard<std::mutex> lock(_mtx);
    _level = level;
    _mode = LO_CONSOLE;
    if (!filename.empty()) {
        setFileName(filename);
        _mode |= LO_FILE;
        _file = fopen(_filepath.c_str(), "w");
    }
}

void Logger::setFileName(const std::string& fileName) {
    baseFileName = fileName;
    char ts[64];
    time_t t = time(nullptr);
    strftime(ts, sizeof(ts), ".%y%m%d-%H%M.txt", localtime(&t));
    _filepath = fileName + ts;
}

std::string Logger::getCurrentTimestamp() {
    using namespace std::chrono;
    auto now = system_clock::now();
    auto t = system_clock::to_time_t(now);
    auto ms = duration_cast<milliseconds>(now.time_since_epoch()) % 1000;
    char buf[64];
    std::tm tm;
#ifdef _WIN32
    localtime_s(&tm, &t);
#else
    localtime_r(&t, &tm);
#endif
    snprintf(buf, sizeof(buf), "%04d-%02d-%02d %02d:%02d:%02d.%03d",
        tm.tm_year + 1900, tm.tm_mon + 1, tm.tm_mday,
        tm.tm_hour, tm.tm_min, tm.tm_sec, (int)ms.count());
    return buf;
}

std::string Logger::buildLogLine(const std::string& funcName, const std::string& buf) {
    return "[" + getCurrentTimestamp() + "] [" + funcName + "] " + buf + "\n";
}

void Logger::logArgs(int level, const std::string& funcName, const char* format, va_list args) {
    if (_level < level) return;

    char msg[MAX_LOG_LEN];
    vsnprintf(msg, sizeof(msg), format, args);

    std::string str = buildLogLine(funcName, msg);

    std::lock_guard<std::mutex> lock(_mtx);

    if (_mode & LO_CONSOLE) {
        fputs(str.c_str(), stdout);
    }
    if ((_mode & LO_FILE) && _file) {
        fputs(str.c_str(), _file);
        fflush(_file);
    }
#ifdef _WIN32
    if (_mode & LO_DEBUGGER) {
        OutputDebugStringA(str.c_str());
    }
#endif
}

void Logger::log(const std::string& funcName, int level, const char* format, ...) {
    if (_level < level) return;
    va_list args;
    va_start(args, format);
    logArgs(level, funcName, format, args);
    va_end(args);
}

void Logger::data(const std::string& funcName, int level, const char* title, const byte* data, unsigned int len) {
    if (_level < level) return;

    log(funcName, level, "%s", title);

    char line[64];
    unsigned pos = 0;
    for (unsigned i = 0; i < len && i < MAX_DATA_LEN; i++) {
        int n = snprintf(line + pos, sizeof(line) - pos, "%02X ", data[i]);
        pos += n;
        if ((i + 1) % 16 == 0 || i == len - 1) {
            log(funcName, level, "%s", line);
            pos = 0;
        }
    }
}
