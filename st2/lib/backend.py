"""Execution backend selection.

Provides a unified interface for running operations via either:
- Python/CFFI implementation (preferred, debuggable)
- C subprocess (for debugging/parity testing)

The CFFI backend is preferred.
"""

from __future__ import annotations

import logging
import subprocess
import time
from collections.abc import Callable, Generator
from contextlib import contextmanager
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, TypeVar

logger = logging.getLogger(__name__)

T = TypeVar("T")


class Backend(str, Enum):
    """Execution backend options."""

    PYTHON = "python"  # Pure Python / CFFI (preferred)
    C = "c"  # Shell out to C binaries


@dataclass
class BackendConfig:
    """Configuration for backend selection."""

    # Default backend for each operation (operation -> backend)
    defaults: dict[str, Backend] = field(default_factory=dict)

    # Global default when operation not in defaults
    global_default: Backend = Backend.PYTHON

    # Available C binaries (operation -> path)
    c_binaries: dict[str, Path] = field(default_factory=dict)

    def get_backend(self, operation: str) -> Backend:
        """Get the backend to use for an operation."""
        backend = self.defaults.get(operation, self.global_default)

        # Fall back to Python if C binary not available
        if backend == Backend.C and operation not in self.c_binaries:
            logger.debug("C binary for %s not available, using Python", operation)
            backend = Backend.PYTHON

        return backend

    def set_default(self, operation: str, backend: Backend) -> None:
        """Set the default backend for an operation."""
        self.defaults[operation] = backend


def check_binary(path: Path | str) -> bool:
    """Check if a binary exists and is executable."""
    path = Path(path)
    return path.exists() and path.is_file()


def run_binary(
    binary: Path | str,
    args: list[str],
    cwd: Path | None = None,
    env: dict[str, str] | None = None,
) -> subprocess.CompletedProcess[str]:
    """Run a binary with arguments.

    Args:
        binary: Path to binary
        args: Command line arguments
        cwd: Working directory
        env: Environment variables (merged with current env)

    Returns:
        CompletedProcess with stdout/stderr

    Raises:
        subprocess.CalledProcessError: If binary returns non-zero
    """
    import os

    cmd = [str(binary), *args]

    full_env = os.environ.copy()
    if env:
        full_env.update(env)

    logger.debug("Running: %s", " ".join(cmd))
    return subprocess.run(
        cmd,
        cwd=cwd,
        env=full_env,
        capture_output=True,
        text=True,
        check=True,
    )


# =============================================================================
# Stats tracking (for profiling/benchmarking)
# =============================================================================


@dataclass
class ExecutionStats:
    """Stats for a single execution."""

    operation: str
    backend: Backend
    duration_seconds: float
    input_size: int  # e.g., number of frames, utterances
    success: bool
    error: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def throughput(self) -> float:
        """Return throughput (items per second)."""
        if self.duration_seconds <= 0:
            return 0.0
        return self.input_size / self.duration_seconds


class StatsTracker:
    """Tracks execution statistics across runs.

    Useful for profiling and comparing backend performance.
    """

    def __init__(self, stats_file: Path | None = None) -> None:
        self.stats_file = stats_file
        self._stats: list[ExecutionStats] = []
        if stats_file and stats_file.exists():
            self._load()

    def _load(self) -> None:
        """Load stats from file."""
        import json

        if not self.stats_file:
            return
        try:
            data = json.loads(self.stats_file.read_text())
            for item in data:
                item["backend"] = Backend(item["backend"])
                self._stats.append(ExecutionStats(**item))
        except (json.JSONDecodeError, KeyError, ValueError) as e:
            logger.warning("Failed to load stats: %s", e)

    def _save(self) -> None:
        """Save stats to file."""
        import json

        if not self.stats_file:
            return
        data = []
        for s in self._stats:
            d = {
                "operation": s.operation,
                "backend": s.backend.value,
                "duration_seconds": s.duration_seconds,
                "input_size": s.input_size,
                "success": s.success,
                "error": s.error,
                "metadata": s.metadata,
            }
            data.append(d)
        self.stats_file.parent.mkdir(parents=True, exist_ok=True)
        self.stats_file.write_text(json.dumps(data, indent=2))

    def record(self, stats: ExecutionStats) -> None:
        """Record execution stats."""
        self._stats.append(stats)
        self._save()

    def get_stats(self, operation: str | None = None) -> list[ExecutionStats]:
        """Get stats, optionally filtered by operation."""
        if operation is None:
            return list(self._stats)
        return [s for s in self._stats if s.operation == operation]

    def avg_throughput(self, operation: str, backend: Backend) -> float | None:
        """Get average throughput for an operation/backend combo."""
        matching = [
            s
            for s in self._stats
            if s.operation == operation and s.backend == backend and s.success
        ]
        if not matching:
            return None
        return sum(s.throughput() for s in matching) / len(matching)

    def recommended_backend(self, operation: str) -> Backend:
        """Recommend a backend based on historical stats."""
        python_tp = self.avg_throughput(operation, Backend.PYTHON)
        c_tp = self.avg_throughput(operation, Backend.C)

        if python_tp is None and c_tp is None:
            return Backend.PYTHON  # Default to Python if no data
        if python_tp is None:
            return Backend.C
        if c_tp is None:
            return Backend.PYTHON

        # Choose faster one, with some threshold to avoid flipping
        if c_tp > python_tp * 1.2:  # C must be 20% faster to prefer
            return Backend.C
        return Backend.PYTHON

    def summary(self, operation: str | None = None) -> str:
        """Generate a summary of stats."""
        stats = self.get_stats(operation)
        if not stats:
            return "No stats recorded."

        lines = []
        operations = sorted({s.operation for s in stats})
        for op in operations:
            op_stats = [s for s in stats if s.operation == op]
            lines.append(f"\n{op}:")
            for backend in [Backend.PYTHON, Backend.C]:
                b_stats = [s for s in op_stats if s.backend == backend and s.success]
                if b_stats:
                    avg_dur = sum(s.duration_seconds for s in b_stats) / len(b_stats)
                    avg_tp = sum(s.throughput() for s in b_stats) / len(b_stats)
                    lines.append(
                        f"  {backend.value}: {len(b_stats)} runs, "
                        f"avg {avg_dur:.2f}s, {avg_tp:.1f} items/s"
                    )
        return "\n".join(lines)


@contextmanager
def profile_execution(
    operation: str,
    backend: Backend,
    input_size: int,
    tracker: StatsTracker | None = None,
    metadata: dict[str, Any] | None = None,
) -> Generator[dict[str, Any], None, None]:
    """Context manager to profile an execution.

    Usage:
        tracker = StatsTracker()
        with profile_execution("bw_iteration", Backend.PYTHON, n_frames, tracker) as ctx:
            result = do_work()
            ctx["result"] = result

    The stats are automatically recorded on exit.
    """
    ctx: dict[str, Any] = {"result": None, "error": None}
    start = time.perf_counter()
    success = False
    error = None

    try:
        yield ctx
        success = True
    except Exception as e:
        error = str(e)
        ctx["error"] = error
        raise
    finally:
        duration = time.perf_counter() - start
        stats = ExecutionStats(
            operation=operation,
            backend=backend,
            duration_seconds=duration,
            input_size=input_size,
            success=success,
            error=error,
            metadata=metadata or {},
        )
        if tracker is not None:
            tracker.record(stats)
        logger.debug(
            "%s via %s: %.2fs for %d items (%.1f/s)",
            operation,
            backend.value,
            duration,
            input_size,
            stats.throughput(),
        )


def run_with_backend(
    operation: str,
    python_impl: Callable[[], T],
    c_impl: Callable[[], T] | None = None,
    input_size: int = 0,
    config: BackendConfig | None = None,
    tracker: StatsTracker | None = None,
) -> T:
    """Run an operation using the configured backend.

    Args:
        operation: Name of the operation (for config lookup and stats)
        python_impl: Python implementation (callable, no args)
        c_impl: C implementation (callable, no args), or None if not available
        input_size: Size of input for throughput calculation
        config: Backend configuration
        tracker: Stats tracker (optional)

    Returns:
        Result from whichever implementation runs
    """
    if config is None:
        config = BackendConfig()

    backend = config.get_backend(operation)

    # Fall back to Python if C not available
    if backend == Backend.C and c_impl is None:
        logger.debug("No C implementation for %s, using Python", operation)
        backend = Backend.PYTHON

    impl = c_impl if backend == Backend.C else python_impl

    with profile_execution(operation, backend, input_size, tracker):
        return impl()


__all__ = [
    "Backend",
    "BackendConfig",
    "ExecutionStats",
    "StatsTracker",
    "check_binary",
    "profile_execution",
    "run_binary",
    "run_with_backend",
]
