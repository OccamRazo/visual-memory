"""Linux Landlock allowlist for normal-reader workers, including when run as root.

The trusted parent handles evaluation and inference; a worker only receives public
questions/query keys and a single sealed snapshot. No gold or source mount is
available to it. Landlock is fail-closed: absence means no valid E2 run.
"""
from __future__ import annotations
import ctypes
import errno
import os
from pathlib import Path

# Linux 5.13+ ABI 1 access rights. Do not ask for rights from a newer ABI.
_EXECUTE=1 << 0
_WRITE_FILE=1 << 1
_READ_FILE=1 << 2
_READ_DIR=1 << 3
_ALL=(1 << 13)-1
class _Ruleset(ctypes.Structure):
    _fields_=[('handled_access_fs',ctypes.c_uint64)]
class _PathBeneath(ctypes.Structure):
    _pack_=1
    _fields_=[('allowed_access',ctypes.c_uint64),('parent_fd',ctypes.c_int32)]

def restrict_read_paths(paths):
    libc=ctypes.CDLL(None,use_errno=True)
    abi=libc.syscall(444,0,0,1)
    if abi < 1:
        raise RuntimeError('Landlock unavailable; normal-reader isolation cannot pass')
    attr=_Ruleset(_ALL)
    fd=libc.syscall(444,ctypes.byref(attr),ctypes.sizeof(attr),0)
    if fd < 0:
        raise OSError(ctypes.get_errno(),'landlock_create_ruleset')
    try:
        for path in paths:
            p=Path(path).resolve(strict=True)
            pfd=os.open(p,os.O_PATH|os.O_CLOEXEC)
            try:
                rights=_READ_FILE|(_READ_DIR if p.is_dir() else 0)
                rule=_PathBeneath(rights,pfd)
                if libc.syscall(445,fd,1,ctypes.byref(rule),0)!=0:
                    raise OSError(ctypes.get_errno(),'landlock_add_rule')
            finally:
                os.close(pfd)
        if libc.prctl(38,1,0,0,0)!=0:
            raise OSError(ctypes.get_errno(),'PR_SET_NO_NEW_PRIVS')
        if libc.syscall(446,fd,0)!=0:
            raise OSError(ctypes.get_errno(),'landlock_restrict_self')
    finally:
        os.close(fd)
    return int(abi)

def probe_isolation(allowed_file, forbidden_files):
    """Call only in a disposable process: this restriction is irreversible."""
    abi=restrict_read_paths([allowed_file])
    with open(allowed_file,'rb') as f:
        f.read(1)
    results={}
    for p in forbidden_files:
        try:
            with open(p,'rb') as f:
                f.read(1)
            results[str(p)]='UNEXPECTED_READ'
        except PermissionError:
            results[str(p)]='denied'
        except FileNotFoundError:
            results[str(p)]='missing_not_a_valid_probe'
    return {'abi':abi,'probes':results,'passed':bool(results) and all(x=='denied' for x in results.values())}
