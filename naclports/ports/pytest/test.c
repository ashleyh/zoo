#include <Python.h>
#include <nacl/nacl_srpc.h>

extern int Py_NoSiteFlag;


int main() {
    puts("Start python test");
    Py_SetPythonHome("/");
    Py_Initialize();
    PyRun_SimpleString("import sys; sys.argv = ['foo', '-x', 'test_dummy_threading']; import test.regrtest; test.regrtest.main()");
    Py_Finalize();
    puts("End python test");
    return 0;
}
