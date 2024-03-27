#pragma once



#include <string>

class StdCapture
{
public:
    StdCapture();
    ~StdCapture();

    void BeginCapture();
    bool EndCapture();
    std::string GetCapture() const;

private:
    enum PIPES { READ, WRITE };
    int m_pipe[2];
//    int m_oldStdOut;
    int m_oldStdErr;
    bool m_capturing;
    bool m_init;
    std::string m_captured;
};