#pragma once

#include <stdarg.h>
#include <string>
#include <mutex>

using byte = unsigned char;   // <-- fix for undefined "byte"
#define MAX_LOG_LEN   18000
#define MAX_DATA_LEN  128

#define LO_CONSOLE   (1)
#define LO_FILE      (2)
#define LO_DEBUGGER  (8)

#define LOG_INIT     Logger::logger.init
#define LOG(...)     Logger::logger.log(__FUNCTION__, __VA_ARGS__)
#define LOG_DATA(...) Logger::logger.data(__FUNCTION__, __VA_ARGS__)

#define LOGE(...) LOG(Log::eErr, __VA_ARGS__)
#define LOGW(...) LOG(Log::eInfo, __VA_ARGS__)
#define LOGI(...) LOG(Log::eInfo, __VA_ARGS__)
#define LOGS(...) LOG(Log::eStream, __VA_ARGS__)
#define LOGSD(...) LOG(Log::eStreamDbg, __VA_ARGS__)
#define LOGD(...) LOG(Log::eStream, __VA_ARGS__)

namespace Log {
    enum {
        eErr = 1,
        eInfo,
        eStream,
        eStreamDbg
    };
};

class Logger {
public:
    static Logger logger;

    Logger();
    ~Logger();

    void init(int level, const std::string& filename = "");
    void log(const std::string& funcName, int level, const char* format, ...);
    void data(const std::string& funcName, int level, const char* title, const byte* buf, unsigned int len);

    void setLogLevel(int level) { _level = level; }
    void setMode(int mode) { _mode = mode; }

    const std::string& getBaseFileName() const { return baseFileName; }
    const std::string& getFileName() const { return _filepath; }
    void setFileName(const std::string& fileName);

private:
    void logArgs(int level, const std::string& funcName, const char* format, va_list args);
    std::string buildLogLine(const std::string& funcName, const std::string& buf);
    std::string getCurrentTimestamp();

    int _mode;
    int _level;

    std::string _filepath;
    std::string baseFileName;

    FILE* _file;
    std::mutex _mtx;
};
