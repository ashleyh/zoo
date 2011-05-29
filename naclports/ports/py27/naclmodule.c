#include <sys/types.h>
#include <pwd.h>
#include <signal.h>
#include <errno.h>
#include <stdio.h>

#define warn(fmt, ...) fprintf(stderr, fmt "\n", ##__VA_ARGS__)

int unlink(const char* p) {
    warn("try unlink %s", p);
    errno = EACCES;
    return -1;
}

int kill(pid_t pid, int sig) {
    warn("try kill %d %d", pid, sig);
    errno = EACCES;
    return -1;
}

char* getcwd(char* buf, size_t size) {
    warn("try getcwd");
    buf[0] = '/';
    buf[1] = 0;
    return buf;
}

int fsync(int fd) {
    errno = ENOSYS;
    return -1;
}

int fdatasync(int fd) {
    errno = ENOSYS;
    return -1;
}


void initnacl(void) {
    puts("hello from nacl");
    return;
}

