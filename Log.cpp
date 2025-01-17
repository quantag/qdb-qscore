/*
 * Copyright (c) 2024 Quantag IT Solutions GmbH
 *
 * This source code is licensed under the MIT license found in the
 * LICENSE file in the root directory of this source tree.
 */


#include "Log.h"
#include <stdio.h>
#include <time.h>
#include <stdarg.h>
#include <ctime>
#include <chrono>
#include <iomanip>
#include <sstream>

#ifdef WIN32
	#include <windows.h>
	#include <direct.h>
#else
	#include <unistd.h>
#endif


#define MAX_LOG_LEN		18000
#define MAX_DATA_LEN	128

/**
 * Global logger
 */
Logger Logger::logger;


Logger::Logger() : _mode(0), _level(0) {
}

Logger::~Logger() {
}


void Logger::init(int level, const std::string& filename) {
	_mode	=  LO_CONSOLE;
	_level	= level;

	if (!filename.empty()) {
		setFileName(filename);
		_mode |= LO_FILE;

		if (_mode & LO_FILE) {
			FILE* fp = fopen(_filepath.c_str(), "w");
			if (fp)
				fclose(fp);
		}
	}
}

void Logger::setFileName(const std::string& fileName) { 
	baseFileName = fileName;

	time_t t = time(NULL);
	struct tm *tmp = localtime(&t);
	char ts[200];
	strftime(ts, 200, ".%y%m%d-%H%M.txt", tmp);

	_filepath = fileName + ts;
}

std::string Logger::getCurrentTimestamp() {
	// Get current time
	auto now = std::chrono::system_clock::now();

	// Convert to time_t
	auto now_time_t = std::chrono::system_clock::to_time_t(now);
	auto now_ms = std::chrono::duration_cast<std::chrono::milliseconds>(now.time_since_epoch()) % 1000;

	// Format time
	std::tm* tm = std::localtime(&now_time_t);
	std::ostringstream oss;
	oss << std::put_time(tm, "%Y-%m-%d %H:%M:%S") << '.' << std::setfill('0') << std::setw(3) << now_ms.count();

	return oss.str();
}

std::string Logger::buildLogLine(const std::string& funcName, const std::string& buf) {
	std::string str = "[" + getCurrentTimestamp() + "]   [" + funcName + "] " + buf + "\n";
	return str;
}

void Logger::logArgs(int level, const std::string &funcName, const char *format, va_list args) {
	char buf[ MAX_LOG_LEN + 1 ];
	/*int len =*/ vsnprintf( buf, MAX_LOG_LEN, format, args );
	buf[ MAX_LOG_LEN ] = '\x0';

	std::string str = buildLogLine(funcName, buf);

	if( _mode & LO_CONSOLE ) {
#ifndef RUN_AS_SERVICE
		printf( "%s", str.c_str() );
#endif
	}
	if( _mode & LO_FILE ) 
	{
		FILE *fp = fopen( _filepath.c_str(), "a" );
		if( fp )
		{
			fputs( str.c_str(), fp );
			fclose( fp );
		}
	}
	if( _mode & LO_DEBUGGER )
	{
#ifdef WIN32
		::OutputDebugStringA( str.c_str() );
#else
#ifndef RUN_AS_SERVICE
		printf( "%s", str.c_str() );
#endif
#endif
	}
}

void Logger::log(const std::string &funcName, int level, const char *format, ...) {
	if( _level < level )
		return;
	va_list	args;
	va_start( args, format );
	logArgs( level, funcName, format, args );
	va_end( args );
}

void Logger::data(const std::string &funcName, int level, const char *title, const byte *data, unsigned int len) {
	if( _level < level )
		return;
	log(funcName, level, title);

	char str[ 100 ];
	int pos = 0;
	int bytesPerLine = 0;
	size_t sz = len;

#ifdef MAX_DATA_LEN
	if(sz>MAX_DATA_LEN) sz = MAX_DATA_LEN;
#endif

	for(size_t i=0; i<sz; i ++) {
		if(bytesPerLine > 0 && ( bytesPerLine % 16 ) == 0) {
			log( funcName, level, str );
			pos = bytesPerLine = 0;
		}
		int n = sprintf( &str[pos], "%02X ", data[ i ] );
		pos += n;
		bytesPerLine ++;
	}
	if( pos )
		log(funcName, level, str);
}
