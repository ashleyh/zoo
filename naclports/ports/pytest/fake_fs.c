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

#include <unistd.h>
#include <errno.h>
#include <sys/stat.h>
#include <stdio.h>
#include <stdlib.h>

#define FD_TABLE_SIZE 256

struct my_fs_entry {
    const char* name;
    mode_t mode;
    size_t size;
    const char* data;
} ;

struct my_fs_entry fs_entries[] = {
//#include "fake_fs_entries"
    {"/usr", S_IFDIR|S_IRUSR|S_IXUSR, 0, NULL},
    {"/usr/local", S_IFDIR|S_IRUSR|S_IXUSR, 0, NULL},
    {"/usr/local/lib", S_IFDIR|S_IRUSR|S_IXUSR, 0, NULL},
    {"/usr/local/lib/python2.7", S_IFDIR|S_IRUSR|S_IXUSR, 0, NULL},
    {"/usr/local/lib/python2.7/os.py", S_IFREG|S_IRUSR, 0, NULL},
    {"/usr/local/lib/python2.7/lib-dynload", S_IFDIR|S_IRUSR|S_IXUSR, 0, NULL},
    {"/usr/local/lib/python2.7/lib-dynload/site.py", S_IFREG|S_IRUSR, 0, NULL},
    {NULL, 0, 0, NULL}
} ;

struct my_fd {
    int fs_entry_index;
    int cursor;
} ;

struct my_fd* fd_table[FD_TABLE_SIZE] = { NULL };

int
stat_impl(int fs_entry_index, struct stat* buf) {
    struct my_fs_entry* fs_entry;

    fs_entry = &fs_entries[fs_entry_index];

    buf->st_dev = 0;
    buf->st_ino = 0;
    buf->st_mode = fs_entry->mode;
    buf->st_nlink = 1;
    buf->st_uid = 0;
    buf->st_gid = 0;
    buf->st_rdev = 0;
    buf->st_size = fs_entry->size;
    buf->st_blocks = fs_entry->size/512;
    buf->st_blksize = buf->st_blocks*512;
    buf->st_atime = 0;
    buf->st_mtime = 0;
    buf->st_ctime = 0;

    return 0;
}

int
find_fs_entry(const char* path) {
    int i;
    for (i = 0; fs_entries[i].name != NULL; i++) {
        if (strcmp(fs_entries[i].name, path) == 0) {
            return i;
        }
    }
    return -1;
}

off_t
__real_lseek (int fd, off_t offset, int whence);

int
underlying_fd_available(int fd) {
    if (__real_lseek(fd, 0, SEEK_CUR) == (off_t)(-1)) {
        if (errno == EBADF) {
            return 1;
        } else {
            /* lseek can also fail on pipes */
            return 0; 
        }
    } else {
        return 0;
    }
}

int
fd_available(int fd) {
    return (fd_table[fd] == NULL) && underlying_fd_available(fd);
} 

int
new_fd(int* fd, struct my_fd** fd_struct) {
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

int
__real_fstat(int fs, struct stat* buf);

int
__wrap_fstat(int fs, struct stat* buf) {
    struct my_fd* fd_struct = fd_table[fs];
    if (fd_struct == NULL) {
        return __real_fstat(fs, buf);
    } else {
        return stat_impl(fd_struct->fs_entry_index, buf);
    }
}

size_t
__wrap_readlink(const char* path, char* buf, size_t bufsiz) {
    /* there are no links on this fake filesystem */
    errno = EINVAL;
    return -1;
}

int
__real_open(const char* path, int flags);

int
__wrap_open(const char* path, int flags) {
    int i;
    printf("__wrap_open(%s, %d)\n", path, flags);
    i = find_fs_entry(path);
    if (i < 0) {
        errno = ENOENT;
        return -1;
    } else {
        struct my_fd* fd_struct;
        int fd;
        int result = new_fd(&fd, &fd_struct);

        if (result < 0) {
            errno = EMFILE;
            return -1;
        } else {
            fd_struct->fs_entry_index = i;
            fd_struct->cursor = 0;
            return fd;
        }
    }
}

int
__real_stat(const char* path, struct stat* buf);    

int
__wrap_stat(const char* path, struct stat* buf) {
    int i;

    
    i = find_fs_entry(path);
    
    printf("__wrap_stat(%s, ...) -> %d\n", path, i);
    if (i < 0) {
        errno = ENOENT;
        return -1;
    } else {
        stat_impl(i, buf);
        return 0;
    }
}

char*
__wrap_getcwd(char* buf, size_t size) {
    printf("__wrap_getcwd(..., %d)\n", size);
    errno = ENOSYS;
    return NULL;
}


ssize_t
__real_write(int fd, const void* buf, size_t count);

ssize_t
__wrap_write(int fd, const void* buf, size_t count) {
#if 0
    /* little test */
    char c = '!';
    __real_write(fd, &c, 1);
#endif
    return __real_write(fd, buf, count);
}


int
__wrap_ftruncate(int fd, off_t length) {
    printf("__wrap_ftruncate(%d, %d)\n", fd, length);
    errno = ENOSYS;
    return -1;
}

off_t
__wrap_lseek(int fd, off_t offset, int whence) {
    struct my_fd* fd_struct = fd_table[fd];
    printf("__wrap_lseek(%d, %d, %d)\n", fd, offset, whence);

    if (fd_struct == NULL) {
        return __real_lseek(fd, offset, whence);
    } else {
        struct my_fs_entry* fs_entry;
        
        fs_entry = &fs_entries[fd_struct->fs_entry_index];
        
        if (whence == SEEK_SET) {
            fd_struct->cursor = offset;
        } else if (whence == SEEK_CUR) {
            fd_struct->cursor += offset;
        } else if (whence == SEEK_END) {
            if (fs_entry->size + offset < 0) {
                errno = EINVAL;
                return -1;
            } else {
                fd_struct->cursor = fs_entry->size + offset;
            }
        } else {
            errno = EINVAL;
            return -1;
        }

        return fd_struct->cursor;
    }            
}


int
__wrap_unlink(const char* pathname) {
    printf("__wrap_unlink(%s)\n", pathname);
    errno = EACCES;
    return -1;
}


int
__wrap_kill(pid_t pid, int sig) {
    printf("__wrap_kill(%d, %d)\n", pid, sig);
    errno = EACCES;
    return -1;
}



int
__real_close(int fd);

int
__wrap_close(int fd) {
    printf("__wrap_close(%d)\n", fd);
    return __real_close(fd);
}


ssize_t
__real_read(int fd, void* buf, size_t count);

ssize_t
__wrap_read(int fd, void* buf, size_t count) {
    printf("__wrap_read(%d, ..., %d)\n", fd, count);
    return __real_read(fd, buf, count);
}

