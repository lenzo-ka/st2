"""CFFI bindings to the st2c library.

This package provides direct access to C functions in libst2c.
For most use cases, prefer the higher-level Python wrappers in st2.lib.

Submodules:
- cdef: C type definitions
- core: FFI initialization and helpers
- io: Model file I/O (read/write mixw, tmat, gau, etc.)
- logmath: Log-domain math wrapper

Usage:
    from st2.lib._cffi import get_ffi, get_lib, path_or_null
    from st2.lib._cffi.io import read_mixw, write_mixw
"""

from st2.lib._cffi.core import get_ffi, get_lib, path_or_null
from st2.lib._cffi.io import (
    read_dnom,
    read_gau,
    read_mixw,
    read_tmat,
    write_dnom,
    write_gau,
    write_mixw,
    write_tmat,
)
from st2.lib._cffi.logmath import LogMath

__all__ = [
    # Core
    "get_ffi",
    "get_lib",
    "path_or_null",
    # I/O
    "read_mixw",
    "write_mixw",
    "read_tmat",
    "write_tmat",
    "read_gau",
    "write_gau",
    "read_dnom",
    "write_dnom",
    # LogMath
    "LogMath",
]
