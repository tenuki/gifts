#!/usr/bin/env python
from abc import abstractmethod, ABC
from pathlib import PurePosixPath as Path
import os
import errno
import socket
import stat
import sys
import unittest

import logging
import logging.handlers

#my_logger = logging.getLogger('MyLogger')
#my_logger.setLevel(logging.DEBUG)
#handler = logging.handlers.SysLogHandler(address='/dev/log')



try:
    import _find_fuse_parts
except ImportError:
    pass
import fuse
from fuse import Fuse
import git
from git import Repo


if not hasattr(fuse, '__version__'):
    raise RuntimeError("your fuse-py doesn't know of fuse.__version__, probably it's too old.")

fuse.fuse_python_api = (0, 2)

serverAddressPort = ("127.0.0.1", 2222)
bufferSize = 1024


def log(*args, **kw):
    UDPClientSocket = socket.socket(family=socket.AF_INET, type=socket.SOCK_DGRAM)
    msg = 'gifts| %s \n' % (' '.join(args))
    bytesToSend = str.encode(msg)
    UDPClientSocket.sendto(bytesToSend, serverAddressPort)


class MyStat(fuse.Stat):
    def __init__(self):
        self.st_mode = 0
        self.st_ino = 0
        self.st_dev = 0
        self.st_nlink = 0
        self.st_uid = 0
        self.st_gid = 0
        self.st_size = 0
        self.st_atime = 0
        self.st_mtime = 0
        self.st_ctime = 0


class NoSuchDir(Exception):
    pass


def b_to_str(full_name):
    name = full_name.split('/', 1)[1]
    return name.replace('/', '__')


def bstr_to_branch(branch):
    return branch.replace('__', '/')


class GitWrapper:
    def __init__(self, repo: Repo):
        self.repo = repo
        self.tree = repo.tree

    def branches(self):
        return {b_to_str(x.name) for x in self.repo.remote().refs}
        #return {x.name for x in self.repo.heads}

    def get_size(self, branch, path, name=None):
        content = self.get_content(branch, path, name)
        return len(content)
        #if name is None: name=''
        #obj = self.get_object(branch, path, name)
        #return obj.size

    def get_content(self, branch, path, name=None):
        if name is None: name = ''
        q = '%s:%s%s'%(branch, path, name)
        data = self.repo.git.show(q)
        return data

    def is_dir(self, branch, path, name):
        obj = self.get_object(branch, path, name)
        if isinstance(obj, git.Blob):
            return False
        if isinstance(obj, git.Tree):
            return True
        raise NoSuchDir()

    def get_object(self, branch, path, name=None):
        if name is None:
            name = ''
        branch_tree = self.tree(branch)
        pointer = branch_tree

        # if not path in ('', '/'):
        comps = path.split('/')
        while comps:
            current = comps.pop(0)
            if current == '': continue
            try:
                pointer = pointer[current]
            except:
                raise NoSuchDir()
        final = pointer
        if name != '':
            try:
                final = final[name]
            except:
                raise NoSuchDir()
        return final


class TreeObjException(Exception):
    pass


class OutsideObject(TreeObjException):
    pass


class NotAFile(TreeObjException):
    pass


class TreeObj(ABC):
    def __init__(self, w: GitWrapper):
        self.w = w

    @classmethod
    def FromPath(cls, w, path):
        _path = Path(path)
        _BranchesPath = Path('/branches')

        if _path == Path('/'):
            return RootPath(w)
        if _path == _BranchesPath:
            return BranchesPath(w)

        _bp = _BranchesPath.parts
        if not _path.parts[:len(_bp)]==_bp:
            raise OutsideObject

        log("parts: %s"%str(_path.parts))  # /,branches,branch_name,etc
        branch = 'origin/'+bstr_to_branch(_path.parts[2])
        comps = _path.parts[3:]
        log("branch:", branch, "parts: %s"%str(comps))
        return RepositoryPath(w, branch, '/'.join(comps))

    @abstractmethod
    def is_dir(self):
        raise NotImplementedError

    def is_file(self):
        return not self.is_dir()

    @abstractmethod
    def get_entries(self):
        raise NotImplementedError

    @abstractmethod
    def get_content(self):
        raise NotImplementedError


class FixedDir(TreeObj, ABC):
    def get_content(self):
        raise NotAFile()

    def is_dir(self):
        return True


class RootPath(FixedDir):
    def get_entries(self):
        return ['.', '..', 'branches']


class BranchesPath(FixedDir):
    def get_entries(self):
        return ['.', '..']+list(self.w.branches())


class RepositoryPath(TreeObj):
    @property
    def obj(self):
        if self._obj is None:
            self._obj = self.w.get_object(self.branch, self.path)
        return self._obj

    def is_dir(self):
        if isinstance(self.obj, git.Blob):
            return False
        if isinstance(self.obj, git.Tree):
            return True
        raise OutsideObject()

    def get_size(self):
        return self.w.get_size(self.branch, self.path)

    def __init__(self, w, branch, pathcomps):
        self._obj = None
        super(RepositoryPath, self).__init__(w)
        self.branch = branch
        self.path = pathcomps

    def get_entries(self):
        if not isinstance(self.obj, git.Tree):
            raise OutsideObject()
        return [x.name for x in self.obj]

    def get_content(self):
        if self.is_dir():
            raise NotAFile()
        return self.w.get_content(self.branch, self.path)


REPO = None   # '/home/aweil/repos/gifts/OMoC-SC-Shared'


class HelloFS:
    def __init__(self):
        assert not(REPO is None)
        self.repo = Repo(REPO)
        self.w = GitWrapper(self.repo)

    def get_object(self, branch, path, name=None):
        return self.w.get_object(branch, path, name)

    #def get_branches(self):
    #    return {branch for branch in self.w.branches()}

    def getattr(self, path):
        log("getattr0: "+path, file=sys.stderr)
        st_dir = MyStat()
        st_dir.st_mode = stat.S_IFDIR | 0o755
        st_dir.st_nlink = 2
        st_file = MyStat()
        st_file.st_mode = stat.S_IFREG | 0o444
        st_file.st_nlink = 1
        try:
            to = TreeObj.FromPath(self.w, path)
            if to.is_dir():
                log("1getattr: " + path+ ' ->dir')
                return st_dir
            st_file.st_size = to.get_size()
            log("2getattr: " + path + ' -> file len: %s'%str(st_file.st_size))
            return st_file
        except (NoSuchDir, OutsideObject) as err:
            log(" (getattr3) exc: "+str(err))
            return -errno.ENOENT
        except Exception as err:
            log(" (getattr4) exc: "+str(err))
            return -errno.ENOENT

    def readdir(self, path, offset):
        log("readdir: "+path, file=sys.stderr)
        try:
            to = TreeObj.FromPath(self.w, path)
            result = to.get_entries()
            log(" +-- entries:"+str(result))
        except Exception as err:
            log(" +-- failure: %s"%err)
            return -errno.ENOENT
        for r in result:
            yield fuse.Direntry(r)

    def open(self, path, flags):
        log("open: "+path, file=sys.stderr)
        try:
            to = TreeObj.FromPath(self.w, path)
            if to.is_dir():
                return -errno.ENOENT
        except:
            return -errno.ENOENT
        accmode = os.O_RDONLY | os.O_WRONLY | os.O_RDWR
        if (flags & accmode) != os.O_RDONLY:
            return -errno.EACCES

    def read(self, path, size, offset):
        log("read: %s - %d"%(path, offset))
        try:
            to = TreeObj.FromPath(self.w, path)
            content = to.get_content().encode('utf-8')
            log(" +- clen "+str(len(content)))
        except Exception as err:
            log(" +- exc1: "+str(err))
            return -errno.ENOENT
        slen = len(content)
        if offset < slen:
            if offset + size > slen:
                size = slen - offset
            buf = content[offset:offset+size]
        else:
            buf = b''
        log(" +- blen "+str(len(buf)))
        log(" +- type "+str(type(buf)))
        return buf


class HelloFUSE(Fuse, HelloFS):
    def __init__(self, *args, **kw):
        super(HelloFUSE, self).__init__(*args, **kw)
        if not hasattr(self, 'w'):
            log("not attr!!!")
            HelloFS.__init__(self)


def main():
    usage="""
Userspace hello example

""" + Fuse.fusage
    server = HelloFUSE(version="%prog " + fuse.__version__,
                     usage=usage,
                     dash_s_do='setsingle')

    server.parse(errex=1)
    server.main()


class TestBasic(unittest.TestCase):
    RepoDir = '/home/aweil/repos/gifts/python-fuse/'

    def setUp(self):
        self.w = GitWrapper(Repo(self.RepoDir))

    def test_isdir(self):
        master = 'master'
        self.assertTrue(self.w.is_dir(master, '/', ''))
        self.assertTrue(self.w.is_dir(master, '/', 'util'))
        self.assertTrue(self.w.is_dir(master, '/util', ''))
        self.assertFalse(self.w.is_dir(master, '/', 'INSTALL'))
        self.assertFalse(self.w.is_dir(master, '', 'INSTALL'))
        self.assertFalse(self.w.is_dir(master, '/util', 'voidspace-fusepy.css'))

        with self.assertRaises(NoSuchDir):
            self.w.is_dir(master, '/util/xxx', '')
        with self.assertRaises(NoSuchDir):
            self.w.is_dir(master, '/util', 'xxx')

    def test_content_and_size(self):
        master = 'master'
        self.assertEqual(len(self.w.get_content(master, '', 'INSTALL')), 1783)
        self.assertEqual(1784, self.w.get_size(master, '', 'INSTALL'))


class TestMore(unittest.TestCase):
    RepoDir = '/home/aweil/repos/gifts/python-fuse/'
    def setUp(self) -> None:
        self.fuse = HelloFS()
        self.w = GitWrapper(Repo(self.RepoDir))

    def test_1(self):
        self.assertEqual(
            self.fuse.getattr('.'),
            6
        )

if __name__ == '__main__':
    import sys
    REPO = sys.argv.pop(1)
    print('REPO is:', REPO)
    main()
