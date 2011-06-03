/* fake_fs.c - trick the interpreter into thinking a filesystem is present
 *
 * Copyright 2011 Ashley Hewson
 * 
 * This file is part of Compiler Zoo.
 * 
 * Compiler Zoo is free software: you can redistribute it and/or modify
 * it under the terms of the GNU General Public License as published by
 * the Free Software Foundation, either version 3 of the License, or
 * (at your option) any later version.
 * 
 * Compiler Zoo is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 * GNU General Public License for more details.
 * 
 * You should have received a copy of the GNU General Public License
 * along with Compiler Zoo.  If not, see <http://www.gnu.org/licenses/>.
 */

/* we get ld to hijack various library calls with the flag
 * -Wl,--wrap=function_name. the new implementation goes in
 * __wrap_function_name and the real one is available through
 * __real_function_name.
 */

/* XXX: need to go through and add cleanup code */

#include <unistd.h>
#include <errno.h>
#include <sys/stat.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/nacl_syscalls.h>
#include <sys/nacl_imc_api.h>
#include <fcntl.h>
#include <dirent.h>

#define DEBUG if(0)

#define FD_TABLE_SIZE 256
#define SOCK 3

struct tmpfs_entry {
    struct tmpfs_entry* next;
    struct tmpfs_entry* prev;

    char* name;
    char* contents;  /* the whole contents of the file */
    int32_t size;    /* apparent size of contents */
    int32_t actual_size; /* size of buffer allocated */
    mode_t st_mode;  /* for fstat */
    char unlink_on_close;
};

struct tmpfs_entry* tmpfs = NULL;
struct tmpfs_entry* tmpfs_end = NULL;

/* describes an open file in the fake filesystem */
struct my_fd {
    struct tmpfs_entry* backing; 
    off_t cursor;    /* current offset into contents */
    int flags;       /* flags passed to open() */
} ;

/* the table of open files */
struct my_fd* fd_table[FD_TABLE_SIZE] = { NULL };

/* what gets sent over imc to open a file */
struct my_open_request {
    char path[256];
    int flags;
};

/* what gets received from imc to open a file */
struct my_open_response {
    int32_t status;
    int32_t size;
};

/* what gets sent over imc to stat a file */
struct my_stat_request {
    char path[256];
};

/* what gets received from imc to stat a file */
struct my_stat_response {
    int32_t status;
    int32_t st_mode;
    int32_t st_size;
};

/* chunk of data, see read_all */
struct read_block {
    uint32_t start;
    uint8_t len;
    char data[256-5];
};


/* the real versions of hijacked library calls */
int __real_fstat(int fs, struct stat* buf);
off_t __real_lseek (int fd, off_t offset, int whence);
int __real_open(const char* path, int flags);
int __real_stat(const char* path, struct stat* buf);    
ssize_t __real_write(int fd, const void* buf, size_t count);
int __real_close(int fd);
int __real_ftruncate(int, off_t);
ssize_t __real_read(int fd, void* buf, size_t count);

/* see canonicalize.c */
char* __realpath(const char*, char*);

char* normalize_path(const char* path) {
    return __realpath(path, NULL);
}

/* this is supposed to be in string.h ...? */
char* strdup(const char* str);

/* this is supposed to be in unistd.h ...? */
int ftruncate(int, off_t);

/* does fd refer to a 'real' fd? */
int underlying_fd_available(int fd) {
    struct stat buf;
    if (__real_fstat(fd, &buf) == 0) {
        return 0;
    } else {
        if (errno == EBADF) {
            return 1;
        } else {
            printf("underlying_fd_available: unexpected errno %d\n", errno);
            return 1; 
        }
    }
}

/* does fd refer to a real or fake fd? */
int fd_available(int fd) {
    return (fd_table[fd] == NULL) && underlying_fd_available(fd);
} 

/* find an entry in the table that doesn't refer to a real or fake fd
 * caller must free fd_struct with free()
 */
int new_fd(int* fd, struct my_fd** fd_struct) {
    int i;
    for (i = 0; i < FD_TABLE_SIZE; i++) {
        if (fd_available(i)) {
            *fd = i;
            fd_table[i] = (struct my_fd*) malloc(sizeof(struct my_fd));
            *fd_struct = fd_table[i];
            return 0;
        }
    }
    return -1;
}

/* fill out a whole struct stat from a couple of fields */
void extend_stat(
    struct stat* buf,
    mode_t st_mode, size_t st_size
) {
    buf->st_dev = 0;
    buf->st_ino = 0;
    buf->st_mode = st_mode;
    buf->st_uid = 0;
    buf->st_gid = 0;
    buf->st_rdev = 0;
    buf->st_size = st_size;
    buf->st_blocks = st_size / 512 + 1;
    buf->st_blksize = buf->st_blocks*512;
    buf->st_atime = 0;
    buf->st_mtime = 0;
    buf->st_ctime = 0;
}


int __wrap_fstat(int fs, struct stat* buf) {
    struct my_fd* fd_struct = fd_table[fs];
    if (fd_struct == NULL) {
        return __real_fstat(fs, buf);
    } else {
        struct tmpfs_entry* tmpf = fd_struct->backing;
        extend_stat(buf, tmpf->st_mode, tmpf->size);
        return 0;
    }
}

size_t __wrap_readlink(const char* path, char* buf, size_t bufsiz) {
    /* there are no links on this fake filesystem */
    errno = EINVAL;
    return -1;
}

/* receive a single blob of data from imc */
void simple_recvmsg(
    int fd,
    void* buf, size_t size
) {
    struct NaClImcMsgHdr header;
    struct NaClImcMsgIoVec iov;
    
    iov.base = buf;
    iov.length = size;
    header.iov = &iov;
    header.iov_length = 1;
    header.descv = NULL;
    header.desc_length = 0;
    header.flags = 0;

    imc_recvmsg(fd, &header, 0);
}
    
/* - i open a socket pair (my_handle, their_handle)
 * - i send (request, their_handle) over SOCK
 * - they write a response to their_handle
 * - i read response from my_handle
 * - i return my_handle as *fd
 * - caller does close(*fd).
 */
void communicate_fd(
    const char* name,
    void* request, size_t request_size, 
    void* response, size_t response_size,
    int* fd
) {
    struct NaClImcMsgHdr header;
    struct NaClImcMsgIoVec iov;
    int sockets[2]; /* the return channel */
    void* buf = malloc(request_size + 4);

    memcpy(buf, name, 4);
    memcpy((char*)buf+4, request, request_size);

    imc_socketpair(sockets);

    iov.base = buf;
    iov.length = request_size + 4;
    header.iov = &iov;
    header.iov_length = 1;
    header.descv = &sockets[1];
    header.desc_length = 1;
    header.flags = 0;


    /* caller's responsiblity to deal with sockets[0] */
    *fd = sockets[0];

    /* send request*/
    imc_sendmsg(SOCK, &header, 0);

    /* we don't need sockets[1] any more on this end */
    __real_close(sockets[1]);

    /* read response */
    simple_recvmsg(sockets[0], response, response_size);
   
}

/* as communicate_fd, but not interested in the fd */
void communicate(
    const char* name,
    void* request, size_t request_size, 
    void* response, size_t response_size
) {
    int fd;
    communicate_fd(
        name,
        request, request_size,
        response, response_size,
        &fd
    );
    __real_close(fd);
}
 
/* read size bytes from fd into dest using a weird little
 * (not at all official) imc-specific protocol
 */
void read_all(
    int fd,
    char* dest, size_t size
) {
    struct read_block blk;
    size_t to_read = size;
    /* i don't really know whether these are received in order
     * so assume they're not
     */
    while (to_read > 0) {
        simple_recvmsg(fd, &blk, sizeof(blk));
        memcpy(&dest[blk.start], &blk.data[0], blk.len);
        to_read -= blk.len;
    }
}

/* open file over imc, put struct in fd_struct, return fake fd */
int open_file_imc(const char* path, int flags, struct my_fd** out_fd_struct) {
    struct my_open_request request;
    struct my_open_response response;
    int response_fd, /* the fd from IMC */
        fake_fd; /* the fd exposed to the app */

    strncpy(request.path, path, 256);
    request.flags = flags;

    communicate_fd(
        "open",
        (void*) &request, sizeof(request),
        (void*) &response, sizeof(response),
        &response_fd
    );

    if (response.status == 0) {
        struct my_fd* fd_struct;
        struct tmpfs_entry* tmpf;
        
        new_fd(&fake_fd, &fd_struct);
        
        tmpf = (struct tmpfs_entry*) malloc(sizeof(*tmpf));
        tmpf->contents = (char*) malloc(response.size);
        tmpf->size = response.size;
        tmpf->actual_size = response.size;
        tmpf->name = NULL;
        tmpf->next = NULL;
        tmpf->prev = tmpfs_end;
        tmpf->unlink_on_close = 1;
        tmpfs_end = tmpf;

        fd_struct->backing = tmpf;
        fd_struct->cursor = 0;
        fd_struct->flags = flags;

        read_all(response_fd, tmpf->contents, response.size);

        __real_close(response_fd);
        DEBUG printf("__wrap_open: fake fd is %d\n", fake_fd);
        *out_fd_struct = fd_struct;
        return fake_fd;
    } else {
        __real_close(response_fd);
        DEBUG printf("__wrap_open: %s: imc error %d\n", path, (int)response.status);
        errno = response.status;
        return -1;
    }
}

/* create new file in the tmpfs */
int create_file_tmpfs(const char* path, int flags, struct my_fd** out_fd_struct) {
    int fake_fd;
    struct my_fd* fd_struct;
    struct tmpfs_entry* tmpf;

    new_fd(&fake_fd, &fd_struct);

    tmpf = (struct tmpfs_entry*) malloc(sizeof(*tmpf));
    tmpf->size = 0;
    tmpf->actual_size = 256;
    tmpf->contents = (char*) malloc(tmpf->actual_size);
    tmpf->name = strdup(path);
    tmpf->next = tmpfs;
    tmpf->prev = NULL;
    tmpf->unlink_on_close = 0;
    tmpfs = tmpf;

    fd_struct->backing = tmpf;
    fd_struct->cursor = 0;
    fd_struct->flags = flags;

    DEBUG printf("__wrap_open: O_CREAT'd fake %d\n", fake_fd);
    *out_fd_struct = fd_struct;
    return fake_fd;
}

void resize(struct tmpfs_entry* tmpf, size_t size) {
    if (size > tmpf->actual_size) {
        tmpf->actual_size *= 2;
        if (size > tmpf->actual_size)
            tmpf->actual_size = size;
        tmpf->contents = realloc(tmpf->contents, tmpf->actual_size);
    }
    tmpf->size = size;
}

int open_file_tmpfs(const char* path, int flags, struct my_fd** out_fd_struct) {
    struct tmpfs_entry* head = tmpfs;
    for (head = tmpfs; head != NULL; head = head->next) {
        if (strcmp(path, head->name) == 0) {
            struct my_fd* fd_struct;
            int fake_fd;
            
            new_fd(&fake_fd, &fd_struct);

            fd_struct->backing = head;
            fd_struct->cursor = 0;
            fd_struct->flags = flags;
            
            *out_fd_struct = fd_struct;
            return fake_fd;
        }
    }

    errno = ENOENT;
    return -1;
}

int my_open(const char* path, int flags, struct my_fd** fd_struct) {
    int fd;

    fd = open_file_imc(path, flags, fd_struct);

    if (fd != -1)
        return fd;
    else if (errno != ENOENT) 
        return -1;

    fd = open_file_tmpfs(path, flags, fd_struct);

    if (fd != -1)
        return fd;
    else if (errno != ENOENT)
        return -1;

    if (flags & O_CREAT)
        return create_file_tmpfs(path, flags, fd_struct); 
    else {
        errno = ENOENT;
        return -1;
    }        
}

int __wrap_open(const char* path, int flags) {
    struct my_fd* fd_struct;
    int fd;
    DEBUG printf("__wrap_open(%s, %o)\n", path, flags);
    fd = my_open(path, flags, &fd_struct);
    if (fd != -1) {
        if (flags & O_TRUNC) {
            ftruncate(fd, 0) ;
        }
        return fd;
    } else {
        return -1;
    }
}





int __wrap_stat(const char* path, struct stat* buf) {
    struct my_stat_request request;
    struct my_stat_response response;
        
    DEBUG printf("__wrap_stat(%s, ...) \n", path);

    strcpy(request.path, path);

    communicate(
        "stat",
        (void*)&request, sizeof(request),
        (void*)&response, sizeof(response)
    );

    if (response.status == 0) {
        extend_stat(buf, response.st_mode, response.st_size);
        return 0;
    } else {
        errno = response.status;
        return -1;
    }    
}

static char* cwd = "/";

char* __wrap_getcwd(char* buf, size_t size) {
    DEBUG printf("__wrap_getcwd(..., %d)\n", size);
    strcpy(buf, cwd);
    return buf;
}


ssize_t __wrap_write(int fd, const void* buf, size_t count) {
    struct my_fd* fd_struct = fd_table[fd];
    if (fd_struct == NULL) {
#if 0
        /* little test */
        char c = '!';
        __real_write(fd, &c, 1);
#endif
        return __real_write(fd, buf, count);
    } else {
        if ((fd_struct->flags & O_WRONLY) || (fd_struct->flags & O_RDWR)) {
            struct tmpfs_entry* tmpf = fd_struct->backing;
            resize(tmpf, fd_struct->cursor + count);
            memcpy(&tmpf->contents[fd_struct->cursor], buf, count);
            fd_struct->cursor += count;
            return count;
        } else {
            errno = EBADF;
            return -1;
        }
    }
}


int __wrap_ftruncate(int fd, off_t length) {
    struct my_fd* fd_struct = fd_table[fd];
    DEBUG printf("__wrap_ftruncate(%d, %d)\n", fd, (int)length);

    if (fd_struct == NULL) {
        return __real_ftruncate(fd, length);
    } else {
        resize(fd_struct->backing, length);
        return 0;
    }
}

off_t __wrap_lseek(int fd, off_t offset, int whence) {
    struct my_fd* fd_struct = fd_table[fd];
    DEBUG printf("__wrap_lseek(%d, %d, %d)\n", fd, (int)offset, whence);

    if (fd_struct == NULL) {
        return __real_lseek(fd, offset, whence);
    } else {
        if (whence == SEEK_SET) {
            fd_struct->cursor = offset;
        } else if (whence == SEEK_CUR) {
            fd_struct->cursor += offset;
        } else if (whence == SEEK_END) {
            if (fd_struct->backing->size + offset < 0) {
                errno = EINVAL;
                return -1;
            } else {
                fd_struct->cursor = fd_struct->backing->size + offset;
            }
        } else {
            errno = EINVAL;
            return -1;
        }

        return fd_struct->cursor;
    }            
}

void my_unlink(struct tmpfs_entry* tmpf) {
    if (tmpf->prev == NULL) {
        tmpfs = tmpf->next;   
    } else {
        tmpf->prev->next = tmpf->next;
    }
    
    if (tmpf->next == NULL) {
        tmpfs_end = tmpf->prev;
    } else {
        tmpf->next->prev = tmpf->prev;
    }

    free(tmpf);
}

int __wrap_unlink(const char* path) {
    struct tmpfs_entry* head = tmpfs;
    for (head = tmpfs; head != NULL; head = head->next) {
        if (strcmp(path, head->name) == 0) {
            my_unlink(head);
            return 0;
        }
    }
    errno = EACCES;
    return -1;
}


int __wrap_kill(pid_t pid, int sig) {
    printf("__wrap_kill(%d, %d)\n", pid, sig);
    errno = EACCES;
    return -1;
}


void destroy_fd(int fd) {
    struct my_fd* fd_struct = fd_table[fd];
    struct tmpfs_entry* tmpf = fd_struct->backing;
    if (tmpf->unlink_on_close)
        my_unlink(tmpf);
    free(fd_struct); 
    fd_table[fd] = NULL;
}

int __wrap_close(int fd) {
    struct my_fd* fd_struct = fd_table[fd];
    DEBUG printf("__wrap_close(%d)\n", fd);
    if (fd_struct == NULL) {
        return __real_close(fd);
    } else {
        destroy_fd(fd);
        return 0;
    }
}

ssize_t __wrap_read(int fd, void* buf, size_t count) {
    struct my_fd* fd_struct = fd_table[fd];
    DEBUG printf("__wrap_read(%d, ..., %d)\n", fd, count);
    
    if (fd_struct == NULL) {
        return __real_read(fd, buf, count);
    } else {

        if (fd_struct->backing->size < fd_struct->cursor) {
            return 0;
        } else {
            char* start = &fd_struct->backing->contents[fd_struct->cursor];
            size_t remaining = fd_struct->backing->size - fd_struct->cursor;
            if (remaining < count)
                count = remaining;            
            memcpy(buf, start, count);
            fd_struct->cursor += count;
            return count;
        }       
    }        
}


#define NOT_IMPL { errno = ENOSYS; return -1; }

int __real_fcntl(int fd, int cmd, ...);

int __wrap_fcntl(int fd, int cmd, ...) NOT_IMPL

int __real_dup(int oldfd);

int __wrap_dup(int oldfd) NOT_IMPL

int __real_dup2(int oldfd, int newfd);

int __wrap_dup2(int oldfd, int newfd) NOT_IMPL

int __wrap_link(const char* oldpath, const char* newpath) NOT_IMPL

int __wrap_symlink(const char* oldpath, const char* newpath) NOT_IMPL

int __wrap_chdir(const char* path) NOT_IMPL

struct my_dir {
    struct my_fd* fd_struct;
    struct dirent dirent_buf;
    int fd;
    int cursor;
};

struct my_dir* __wrap_opendir(const char* name) {
    struct my_dir* dirp;
    dirp = (struct my_dir*) malloc(sizeof(*dirp));
    dirp->fd = my_open(name, O_RDONLY, &dirp->fd_struct);
    dirp->cursor = 0;

    if (dirp->fd == -1) {
        int old_errno = errno;
        DEBUG printf("__wrap_opendir(%s) -> error", name);
        errno = old_errno;
        return NULL;
    } else {
        DEBUG printf("__wrap_opendir(%s) -> %s, ...\n", name, dirp->fd_struct->backing->contents);
        return dirp;
    }
}

struct dirent* __wrap_readdir(struct my_dir* dirp) {
    char name_buf[256];
    int amount_read;

    lseek(dirp->fd, dirp->cursor, SEEK_SET);
    amount_read = read(dirp->fd, name_buf, 256);
    if (amount_read > 0) {
        dirp->cursor += strlen(name_buf) + 1;
        strncpy(dirp->dirent_buf.d_name, name_buf, 256);
        DEBUG printf("__wrap_readdir: returning %d %s\n", amount_read, name_buf);
        return &dirp->dirent_buf;
    } else {
        return NULL;
    }
}

int __wrap_closedir(struct my_dir* dirp) {
    errno = ENOSYS;
    return -1;
}
