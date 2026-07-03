#!/usr/bin/env python3
"""Extract C function signatures from headers for binding generation."""

import re
import subprocess
from pathlib import Path


def preprocess_header(header_path: Path, include_dirs: list[Path]) -> str:
    """Run C preprocessor on header to resolve includes and macros."""
    include_args = [f"-I{d}" for d in include_dirs]
    result = subprocess.run(
        ["cc", "-E", "-P", *include_args, str(header_path)],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        print(f"Warning: preprocessor failed for {header_path}: {result.stderr}")
        return ""
    return result.stdout


def extract_function_decls(header_content: str) -> list[str]:
    """Extract function declarations from preprocessed header content."""
    # Match function declarations (simplified pattern)
    # Looks for: return_type function_name(params);
    pattern = r"""
        ^                           # Start of line
        (?:extern\s+)?              # Optional extern
        (?:static\s+)?              # Optional static
        (?:inline\s+)?              # Optional inline
        (                           # Return type group
            (?:const\s+)?           # Optional const
            (?:unsigned\s+|signed\s+)?  # Optional unsigned/signed
            \w+                     # Base type
            (?:\s*\*+)?             # Optional pointer
        )
        \s+
        (\w+)                       # Function name
        \s*
        \(([^)]*)\)                 # Parameters
        \s*;                        # Semicolon
    """
    matches = re.findall(pattern, header_content, re.MULTILINE | re.VERBOSE)

    decls = []
    for ret_type, func_name, params in matches:
        decls.append(f"{ret_type.strip()} {func_name}({params.strip()});")
    return decls


def extract_from_header_file(header_path: Path) -> list[dict[str, str]]:
    """Extract signatures directly from a header file without preprocessing."""
    content = header_path.read_text()

    # Remove comments
    content = re.sub(r"/\*.*?\*/", "", content, flags=re.DOTALL)
    content = re.sub(r"//.*$", "", content, flags=re.MULTILINE)

    # Find function declarations (multi-line aware)
    # Pattern for: type name(args);
    pattern = r"""
        ^[ \t]*                     # Start of line, optional whitespace
        (                           # Return type
            (?:const\s+)?
            (?:unsigned\s+|signed\s+)?
            (?:struct\s+)?
            \w+                     # type name
            (?:\s*\*+\s*|\s+)       # pointer or space
        )
        (\w+)                       # Function name
        \s*\(\s*
        ([^)]*?)                    # Parameters (non-greedy)
        \s*\)\s*;
    """

    results = []
    for match in re.finditer(pattern, content, re.MULTILINE | re.VERBOSE):
        ret_type = match.group(1).strip()
        func_name = match.group(2)
        params = match.group(3).strip()

        # Clean up params (normalize whitespace)
        params = re.sub(r"\s+", " ", params)

        results.append(
            {
                "name": func_name,
                "return_type": ret_type,
                "params": params,
                "signature": f"{ret_type} {func_name}({params});",
            }
        )

    return results


def scan_headers(include_dir: Path) -> dict[str, list[dict[str, str]]]:
    """Scan all headers in a directory tree."""
    results = {}
    for header in include_dir.rglob("*.h"):
        rel_path = header.relative_to(include_dir)
        funcs = extract_from_header_file(header)
        if funcs:
            results[str(rel_path)] = funcs
    return results


if __name__ == "__main__":
    csrc = Path(__file__).parent.parent / "csrc"
    include_dir = csrc / "include"

    print("Scanning headers...")
    all_funcs = scan_headers(include_dir)

    total = 0
    for header, funcs in sorted(all_funcs.items()):
        print(f"\n{header}:")
        for f in funcs:
            print(f"  {f['signature']}")
            total += 1

    print(f"\n\nTotal functions found: {total}")
