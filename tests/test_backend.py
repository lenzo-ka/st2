"""Tests for backend selection and profiling."""

import tempfile
import time
from pathlib import Path

import pytest

from st2.lib.backend import (
    Backend,
    BackendConfig,
    ExecutionStats,
    StatsTracker,
    profile_execution,
    run_with_backend,
)


class TestExecutionStats:
    """Tests for ExecutionStats."""

    def test_throughput(self) -> None:
        stats = ExecutionStats(
            operation="test",
            backend=Backend.PYTHON,
            duration_seconds=2.0,
            input_size=1000,
            success=True,
        )
        assert stats.throughput() == 500.0

    def test_throughput_zero_duration(self) -> None:
        stats = ExecutionStats(
            operation="test",
            backend=Backend.PYTHON,
            duration_seconds=0.0,
            input_size=1000,
            success=True,
        )
        assert stats.throughput() == 0.0


class TestStatsTracker:
    """Tests for StatsTracker."""

    def test_record_and_retrieve(self) -> None:
        tracker = StatsTracker()
        stats = ExecutionStats(
            operation="bw_iteration",
            backend=Backend.PYTHON,
            duration_seconds=10.0,
            input_size=5000,
            success=True,
        )
        tracker.record(stats)
        retrieved = tracker.get_stats("bw_iteration")
        assert len(retrieved) == 1
        assert retrieved[0].operation == "bw_iteration"

    def test_persistence(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            stats_file = Path(tmpdir) / "stats.json"

            # Record some stats
            tracker1 = StatsTracker(stats_file)
            tracker1.record(
                ExecutionStats(
                    operation="test_op",
                    backend=Backend.PYTHON,
                    duration_seconds=1.0,
                    input_size=100,
                    success=True,
                )
            )

            # Load in new tracker
            tracker2 = StatsTracker(stats_file)
            stats = tracker2.get_stats()
            assert len(stats) == 1
            assert stats[0].operation == "test_op"

    def test_avg_throughput(self) -> None:
        tracker = StatsTracker()
        for dur in [1.0, 2.0, 3.0]:
            tracker.record(
                ExecutionStats(
                    operation="test",
                    backend=Backend.PYTHON,
                    duration_seconds=dur,
                    input_size=100,
                    success=True,
                )
            )

        # Throughputs: 100, 50, 33.33 -> avg ~61.1
        avg = tracker.avg_throughput("test", Backend.PYTHON)
        assert avg is not None
        assert 60 < avg < 62

    def test_recommended_backend_no_data(self) -> None:
        tracker = StatsTracker()
        # Should default to Python with no data
        assert tracker.recommended_backend("unknown") == Backend.PYTHON

    def test_recommended_backend_prefers_faster(self) -> None:
        tracker = StatsTracker()

        # Python: 100 items in 10s = 10/s
        tracker.record(
            ExecutionStats(
                operation="test",
                backend=Backend.PYTHON,
                duration_seconds=10.0,
                input_size=100,
                success=True,
            )
        )

        # C: 100 items in 1s = 100/s (10x faster)
        tracker.record(
            ExecutionStats(
                operation="test",
                backend=Backend.C,
                duration_seconds=1.0,
                input_size=100,
                success=True,
            )
        )

        assert tracker.recommended_backend("test") == Backend.C

    def test_summary(self) -> None:
        tracker = StatsTracker()
        tracker.record(
            ExecutionStats(
                operation="bw_iteration",
                backend=Backend.PYTHON,
                duration_seconds=15.0,
                input_size=5000,
                success=True,
            )
        )

        summary = tracker.summary()
        assert "bw_iteration" in summary
        assert "python" in summary


class TestProfileExecution:
    """Tests for profile_execution context manager."""

    def test_records_success(self) -> None:
        tracker = StatsTracker()

        with profile_execution("test_op", Backend.PYTHON, 100, tracker):
            time.sleep(0.01)

        stats = tracker.get_stats()
        assert len(stats) == 1
        assert stats[0].success is True
        assert stats[0].duration_seconds >= 0.01

    def test_records_failure(self) -> None:
        tracker = StatsTracker()

        with pytest.raises(ValueError):
            with profile_execution("test_op", Backend.PYTHON, 100, tracker):
                raise ValueError("test error")

        stats = tracker.get_stats()
        assert len(stats) == 1
        assert stats[0].success is False
        assert "test error" in (stats[0].error or "")


class TestBackendConfig:
    """Tests for BackendConfig."""

    def test_default_backend(self) -> None:
        config = BackendConfig(global_default=Backend.PYTHON)
        assert config.get_backend("unknown_op") == Backend.PYTHON

    def test_operation_specific_default(self) -> None:
        config = BackendConfig(
            defaults={"bw_iteration": Backend.C},
            c_binaries={"bw_iteration": Path("/usr/bin/bw")},
        )
        assert config.get_backend("bw_iteration") == Backend.C

    def test_falls_back_to_python_if_no_binary(self) -> None:
        config = BackendConfig(
            defaults={"bw_iteration": Backend.C},
            c_binaries={},  # No binary registered
        )
        # Should fall back to Python
        assert config.get_backend("bw_iteration") == Backend.PYTHON


class TestRunWithBackend:
    """Tests for run_with_backend."""

    def test_runs_python_impl(self) -> None:
        result = run_with_backend(
            "test_op",
            python_impl=lambda: "python_result",
            c_impl=lambda: "c_result",
            config=BackendConfig(global_default=Backend.PYTHON),
        )
        assert result == "python_result"

    def test_runs_c_impl_when_configured(self) -> None:
        config = BackendConfig(
            defaults={"test_op": Backend.C},
            c_binaries={"test_op": Path("/fake/path")},
        )
        result = run_with_backend(
            "test_op",
            python_impl=lambda: "python_result",
            c_impl=lambda: "c_result",
            config=config,
        )
        assert result == "c_result"

    def test_falls_back_to_python_if_no_c_impl(self) -> None:
        config = BackendConfig(
            defaults={"test_op": Backend.C},
            c_binaries={"test_op": Path("/fake/path")},
        )
        result = run_with_backend(
            "test_op",
            python_impl=lambda: "python_result",
            c_impl=None,  # No C implementation
            config=config,
        )
        assert result == "python_result"

    def test_tracks_stats(self) -> None:
        tracker = StatsTracker()
        run_with_backend(
            "test_op",
            python_impl=lambda: "result",
            input_size=1000,
            tracker=tracker,
        )

        stats = tracker.get_stats()
        assert len(stats) == 1
        assert stats[0].input_size == 1000
