"""Single source of truth for libst2c availability in the test suite.

Detection is based on whether the library can actually be *loaded* through
the same discovery path the package uses at runtime
(``st2.lib._st2c.get_lib`` → ``st2.lib.paths``), not on hardcoded ``build/``
locations. The old per-file checks only probed ``build/libst2c.{dylib,so}``
and so silently skipped every CFFI test whenever the library lived in
``build/lib/`` (e.g. the CI root-configured build on macOS).

Set ``ST2_REQUIRE_CLIB=1`` to turn "library missing" from a skip into a hard
collection error, so CI asserts the C library was actually exercised instead
of quietly degrading to a Python-only run. See ``conftest.py`` for the gate.
"""

from __future__ import annotations

import functools
import os

import pytest


@functools.lru_cache(maxsize=1)
def c_library_available() -> bool:
    """Return True if libst2c can be loaded via the real discovery path."""
    try:
        from st2.lib._st2c import get_lib

        get_lib()
    except Exception:
        return False
    return True


def require_clib_env() -> bool:
    """True if the environment demands the C library be present (CI gate)."""
    return os.environ.get("ST2_REQUIRE_CLIB", "").strip().lower() in {
        "1",
        "true",
        "yes",
        "on",
    }


C_LIBRARY_AVAILABLE = c_library_available()

requires_c_library = pytest.mark.skipif(
    not C_LIBRARY_AVAILABLE,
    reason="libst2c not loadable (build it: 'make build-c'). "
    "Set ST2_REQUIRE_CLIB=1 to make this a hard failure instead of a skip.",
)
"""Skip a test when libst2c is unavailable (unless ST2_REQUIRE_CLIB gates it)."""
