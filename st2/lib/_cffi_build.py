"""Build cffi bindings for st2c library."""

import re
from pathlib import Path

from cffi import FFI


def get_include_dir() -> Path:
    """Get the include directory for headers."""
    return Path(__file__).parent.parent.parent / "csrc" / "include"


def get_library_dir() -> Path:
    """Get the library directory for the shared library."""
    return Path(__file__).parent.parent.parent / "build" / "lib"


def preprocess_headers() -> str:
    """Preprocess all headers to get declarations for cffi.

    This runs the C preprocessor to expand includes/macros, then
    extracts just the function declarations.
    """
    _ = get_include_dir()  # Validate include dir exists

    # Create a combined header that includes everything
    combined = """
    #include <stdint.h>
    #include <stddef.h>

    // Forward declare opaque types
    typedef struct cmd_ln_s cmd_ln_t;
    typedef struct logmath_s logmath_t;
    typedef struct fe_s fe_t;
    typedef struct feat_s feat_t;
    typedef struct hash_table_s hash_table_t;
    typedef struct hash_iter_s hash_iter_t;
    typedef struct glist_s *glist_t;
    typedef struct gnode_s *gnode_t;
    typedef struct listelem_alloc_s listelem_alloc_t;
    typedef struct yin_s yin_t;
    typedef struct fsg_model_s fsg_model_t;
    typedef struct ngram_model_s ngram_model_t;
    typedef struct acmod_set_s acmod_set_t;
    typedef struct lexicon_s lexicon_t;
    typedef struct model_def_s model_def_t;
    typedef struct model_inventory_s model_inventory_t;
    typedef struct dtree_s dtree_t;
    typedef struct dtree_node_s dtree_node_t;
    typedef struct comp_quest_s comp_quest_t;
    typedef struct pset_s pset_t;
    typedef struct quest_s quest_t;
    typedef struct s3lattice_s s3lattice_t;
    typedef struct s3phseg_s s3phseg_t;
    typedef struct mllr_reg_s mllr_reg_t;

    // Common typedefs
    typedef float float32;
    typedef double float64;
    typedef int int32;
    typedef unsigned int uint32;
    typedef short int16;
    typedef unsigned short uint16;
    typedef char int8;
    typedef unsigned char uint8;
    typedef float32 *vector_t;
    typedef uint32 acmod_id_t;
    typedef uint32 word_posn_t;
    """

    return combined


def extract_cdef_from_headers() -> str:
    """Extract function declarations suitable for cffi cdef."""
    include_dir = get_include_dir()

    # Start with basic types
    cdef_parts = [
        "// Basic types",
        "typedef float float32;",
        "typedef double float64;",
        "typedef int int32;",
        "typedef unsigned int uint32;",
        "typedef short int16;",
        "typedef unsigned short uint16;",
        "typedef char int8;",
        "typedef unsigned char uint8;",
        "typedef float32 *vector_t;",
        "typedef uint32 acmod_id_t;",
        "typedef uint32 word_posn_t;",
        "",
        "// Opaque struct pointers",
        "typedef struct { ...; } cmd_ln_t;",
        "typedef struct { ...; } logmath_t;",
        "typedef struct { ...; } fe_t;",
        "typedef struct { ...; } feat_t;",
        "typedef struct { ...; } hash_table_t;",
        "typedef struct { ...; } hash_iter_t;",
        "typedef struct { ...; } listelem_alloc_t;",
        "typedef struct { ...; } yin_t;",
        "typedef struct { ...; } acmod_set_t;",
        "typedef struct { ...; } lexicon_t;",
        "typedef struct { ...; } model_def_t;",
        "typedef struct { ...; } model_inventory_t;",
        "typedef struct { ...; } dtree_t;",
        "typedef struct { ...; } dtree_node_t;",
        "typedef struct { ...; } pset_t;",
        "typedef struct { ...; } quest_t;",
        "typedef struct { ...; } s3lattice_t;",
        "typedef struct { ...; } s3phseg_t;",
        "typedef struct { ...; } mllr_reg_t;",
        "",
        "// Functions",
    ]

    # Extract function declarations from headers
    for header in sorted(include_dir.rglob("*.h")):
        content = header.read_text()

        # Remove comments
        content = re.sub(r"/\*.*?\*/", "", content, flags=re.DOTALL)
        content = re.sub(r"//.*$", "", content, flags=re.MULTILINE)

        # Find function declarations
        # Pattern: return_type name(args);
        pattern = r"""
            ^[ \t]*
            (
                (?:const\s+)?
                (?:unsigned\s+|signed\s+)?
                (?:struct\s+)?
                \w+
                (?:\s*\*+\s*|\s+)
            )
            (\w+)
            \s*\(\s*
            ([^)]*?)
            \s*\)\s*;
        """

        for match in re.finditer(pattern, content, re.MULTILINE | re.VERBOSE):
            ret_type = match.group(1).strip()
            func_name = match.group(2)
            params = match.group(3).strip()

            # Skip internal/private functions
            if func_name.startswith("_"):
                continue

            # Clean up params
            params = re.sub(r"\s+", " ", params)

            cdef_parts.append(f"{ret_type} {func_name}({params});")

    return "\n".join(cdef_parts)


def build_ffi() -> FFI:
    """Build the FFI object."""
    ffi = FFI()

    cdef = extract_cdef_from_headers()
    ffi.cdef(cdef)

    return ffi


if __name__ == "__main__":
    print(extract_cdef_from_headers())
