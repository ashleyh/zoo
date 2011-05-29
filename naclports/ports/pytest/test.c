#include <Python.h>

extern int Py_NoSiteFlag;

int main() {
    puts("hi");
    Py_NoSiteFlag = 1;
    Py_SetPythonHome("/");
    Py_Initialize();
    PyRun_SimpleString("print 'hai'");
    Py_Finalize();
    return 0;
}
