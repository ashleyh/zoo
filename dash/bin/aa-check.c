#include <unistd.h>
#include <sys/apparmor.h>
#include <error.h>
#include <string.h>
#include <errno.h>
#include <fcntl.h>
#include <stdio.h>


int check1() {
    int f;

    f = open("/proc/self/attr/current", O_RDONLY);

    if (f == -1) {
        if (errno == EACCES) {
            /* this suggests that we're in jail */
            return 0;
        } else {
            /* some unexpected error... */
            perror("error opening /proc/self/attr/current");
            return 1;
        }
    } else {
#       define BUF_SIZE 256
        char buf[BUF_SIZE];
        int n;
        
        n = read(f, (void*)buf, BUF_SIZE);
        close(f);

        if (n == -1) {
            perror("couldn't read /proc/self/attr/current");
            return 1;
        } else {
            if (strncmp(buf, "unconfined", 10) == 0) {
                perror("i don't appear to be in jail");
                return 1;
            } else {
                return 0;
            }
        }        
    }
}



int main(int argc, char** argv) {
    if (check1() != 0) {
        return 1;
    }
    return 0;
}

    


