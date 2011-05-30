#include <Python.h>

extern int Py_NoSiteFlag;

int main() {
    Py_Initialize();
    PyRun_SimpleString("import sys; print 'ohai from python'; print sys.path");
    Py_Finalize();
    return 0;
}
