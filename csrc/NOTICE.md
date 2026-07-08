# Provenance and licensing of `csrc/`

The C substrate in this directory combines vendored CMU Sphinx code with ST2
modifications and new code. Two licenses apply; see below.

## Vendored CMU Sphinx code — modified (CMU BSD + ST2 BSD 2-Clause)

Most of `csrc/` is derived from the **CMU Sphinx** project — specifically
**SphinxTrain**, **SphinxBase**, and **Sphinx-3**:

- `libs/libio/`, `libs/libcommon/`, `libs/libclust/`, `libs/libmllr/`,
  `libs/libmodinv/` — SphinxTrain libraries.
- `libs/libsphinxbase/` — SphinxBase (allocator, cmd_ln, logmath, MFCC
  front-end, feature transforms, and a bundled LAPACK/BLAS-lite fallback).
- `programs/` — the SphinxTrain command-line programs, plus the Sphinx-3
  `sphinx3_align` forced aligner.

These files **have been modified** as part of ST2 (e.g. symbol namespacing for
the Sphinx-3 aligner, `#ifdef ST2_LIBRARY_BUILD` guards that strip `main()` so
program sources can be linked into the shared library, portability and
build-integration fixes). As a result they are effectively **dual-licensed**:

- The original portions remain under the **CMU Sphinx BSD-style license**
  (Copyright (c) 1999–2016 Carnegie Mellon University). Its full text is in
  [`LICENSE.sphinx`](LICENSE.sphinx), and the per-file CMU copyright headers are
  retained as required by that license.
- The ST2 **modifications** are Copyright (c) 2026 Kevin Lenzo and are licensed
  under the **BSD 2-Clause license** (repository root [`LICENSE`](../LICENSE)).

Redistribution must satisfy both licenses; both are permissive BSD-style
and compatible.

Upstream: https://github.com/cmusphinx/sphinxtrain

## New ST2 code — BSD 2-Clause

`libs/libst2/` (the `st2_*.c` / `st2_*.h` session-wrapper layer that exposes a
simplified, CFFI-friendly API over the SphinxTrain internals) and the ST2 build
system are original work, Copyright (c) 2026 Kevin Lenzo, distributed under the
BSD 2-Clause license in the repository root [`LICENSE`](../LICENSE).
