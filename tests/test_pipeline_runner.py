"""Tests for st2.lib.pipeline.runner.

Focus on the runner's behavior in isolation: dependency resolution, topo
sort, staleness detection, dry-run output, and parallel fan-out execution.

These tests use trivial file-touching tasks; they do not exercise any
actual ST2 training code.
"""

from __future__ import annotations

import functools
import time
from pathlib import Path

import pytest

from st2.lib.pipeline import Pipeline, Task, UnknownTargetError


def _touch(path: Path, contents: str = "") -> None:
    """Module-level worker for parallel-execution tests; must be picklable."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(contents)


def _make_touch_task(name: str, out: Path, *, inputs: tuple[Path, ...] = ()) -> Task:
    """A simple task that writes `name` to `out` when executed."""
    return Task(
        name=name,
        fn=functools.partial(_touch, out, name),
        inputs=inputs,
        outputs=(out,),
    )


def test_simple_linear_chain_runs_in_order(tmp_path: Path) -> None:
    """flat -> ci-1g; both outputs missing; both should run, in order."""
    flat = tmp_path / "flat.txt"
    ci = tmp_path / "ci.txt"

    pl = Pipeline()
    pl.add(_make_touch_task("flat", flat))
    pl.add(_make_touch_task("ci-1g", ci, inputs=(flat,)))
    pl.register_target("ci-1g", ci)

    rc = pl.run("ci-1g")
    assert rc == 0
    assert flat.read_text() == "flat"
    assert ci.read_text() == "ci-1g"
    assert flat.stat().st_mtime <= ci.stat().st_mtime


def test_skip_when_up_to_date(tmp_path: Path) -> None:
    """If outputs are newer than inputs, nothing runs and rc=0."""
    flat = tmp_path / "flat.txt"
    ci = tmp_path / "ci.txt"
    flat.write_text("old-flat")
    time.sleep(0.01)
    ci.write_text("old-ci")

    ran: list[str] = []

    def record_and_touch(name: str, out: Path) -> None:
        ran.append(name)
        out.write_text(name)

    pl = Pipeline()
    pl.add(
        Task(
            name="flat",
            fn=functools.partial(record_and_touch, "flat", flat),
            outputs=(flat,),
        )
    )
    pl.add(
        Task(
            name="ci-1g",
            fn=functools.partial(record_and_touch, "ci-1g", ci),
            inputs=(flat,),
            outputs=(ci,),
        )
    )
    pl.register_target("ci-1g", ci)

    rc = pl.run("ci-1g")
    assert rc == 0
    assert ran == []
    assert ci.read_text() == "old-ci"


def test_force_reruns_everything(tmp_path: Path) -> None:
    """--force runs all reachable tasks even if up to date."""
    flat = tmp_path / "flat.txt"
    ci = tmp_path / "ci.txt"
    flat.write_text("old")
    time.sleep(0.01)
    ci.write_text("old")

    ran: list[str] = []

    def record_and_touch(name: str, out: Path) -> None:
        ran.append(name)
        out.write_text(name)

    pl = Pipeline()
    pl.add(
        Task(
            name="flat",
            fn=functools.partial(record_and_touch, "flat", flat),
            outputs=(flat,),
        )
    )
    pl.add(
        Task(
            name="ci-1g",
            fn=functools.partial(record_and_touch, "ci-1g", ci),
            inputs=(flat,),
            outputs=(ci,),
        )
    )
    pl.register_target("ci-1g", ci)

    rc = pl.run("ci-1g", force=True)
    assert rc == 0
    assert ran == ["flat", "ci-1g"]


def test_stale_input_triggers_rerun(tmp_path: Path) -> None:
    """An input newer than any output marks the consumer task stale."""
    flat = tmp_path / "flat.txt"
    ci = tmp_path / "ci.txt"
    ci.write_text("old-ci")
    time.sleep(0.05)
    flat.write_text("new-flat")  # Newer than ci

    ran: list[str] = []

    def record_and_touch(name: str, out: Path) -> None:
        ran.append(name)
        out.write_text(name)

    pl = Pipeline()
    pl.add(
        Task(
            name="flat",
            fn=functools.partial(record_and_touch, "flat", flat),
            outputs=(flat,),
        )
    )
    pl.add(
        Task(
            name="ci-1g",
            fn=functools.partial(record_and_touch, "ci-1g", ci),
            inputs=(flat,),
            outputs=(ci,),
        )
    )
    pl.register_target("ci-1g", ci)

    rc = pl.run("ci-1g")
    assert rc == 0
    assert ran == ["ci-1g"]  # flat is up to date; only ci-1g reruns


def test_dry_run_does_not_execute(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    """Dry-run prints a plan and does not run any task callables."""
    out = tmp_path / "out.txt"
    ran: list[str] = []

    def boom() -> None:
        ran.append("ran")
        raise RuntimeError("should not be called in dry-run")

    pl = Pipeline()
    pl.add(Task(name="t1", fn=boom, outputs=(out,)))
    pl.register_target("t1", out)

    rc = pl.run("t1", dry_run=True)
    assert rc == 0
    assert ran == []
    assert not out.exists()
    captured = capsys.readouterr()
    assert "Plan for target: t1" in captured.out
    assert "t1" in captured.out


def test_unknown_target_raises(tmp_path: Path) -> None:
    pl = Pipeline()
    pl.add(Task(name="t", fn=lambda: None, outputs=(tmp_path / "x",)))
    with pytest.raises(UnknownTargetError):
        pl.run("does-not-exist")


def test_duplicate_outputs_rejected(tmp_path: Path) -> None:
    pl = Pipeline()
    out = tmp_path / "shared.txt"
    pl.add(Task(name="a", fn=lambda: None, outputs=(out,)))
    with pytest.raises(ValueError, match="two tasks produce"):
        pl.add(Task(name="b", fn=lambda: None, outputs=(out,)))


def test_cycle_detected(tmp_path: Path) -> None:
    a = tmp_path / "a.txt"
    b = tmp_path / "b.txt"
    pl = Pipeline()
    pl.add(Task(name="ta", fn=lambda: None, inputs=(b,), outputs=(a,)))
    pl.add(Task(name="tb", fn=lambda: None, inputs=(a,), outputs=(b,)))
    pl.register_target("ta", a)
    with pytest.raises(RuntimeError, match="cycle"):
        pl.plan("ta")


def test_task_failure_returns_nonzero(tmp_path: Path) -> None:
    out = tmp_path / "x.txt"

    def boom() -> None:
        raise RuntimeError("nope")

    pl = Pipeline()
    pl.add(Task(name="t", fn=boom, outputs=(out,)))
    pl.register_target("t", out)
    rc = pl.run("t")
    assert rc != 0
    assert not out.exists()


def test_missing_output_after_run_fails(tmp_path: Path) -> None:
    """A task whose fn returns without producing its declared outputs fails."""
    out = tmp_path / "x.txt"

    def silent() -> None:
        pass  # Don't actually create the file

    pl = Pipeline()
    pl.add(Task(name="t", fn=silent, outputs=(out,)))
    pl.register_target("t", out)
    rc = pl.run("t")
    assert rc != 0


def test_diamond_dependency_visits_each_task_once(tmp_path: Path) -> None:
    """a -> b, a -> c, both -> d. `a` should appear once in the plan."""
    a, b, c, d = (tmp_path / x for x in ["a", "b", "c", "d"])
    ran: list[str] = []

    def record(name: str, out: Path) -> None:
        ran.append(name)
        out.write_text(name)

    pl = Pipeline()
    pl.add(Task("a", functools.partial(record, "a", a), outputs=(a,)))
    pl.add(Task("b", functools.partial(record, "b", b), inputs=(a,), outputs=(b,)))
    pl.add(Task("c", functools.partial(record, "c", c), inputs=(a,), outputs=(c,)))
    pl.add(Task("d", functools.partial(record, "d", d), inputs=(b, c), outputs=(d,)))
    pl.register_target("d", d)

    rc = pl.run("d")
    assert rc == 0
    assert ran.count("a") == 1
    # a must come before b and c; b and c must come before d
    assert ran.index("a") < ran.index("b") < ran.index("d")
    assert ran.index("a") < ran.index("c") < ran.index("d")


def test_external_inputs_are_not_treated_as_tasks(tmp_path: Path) -> None:
    """If a task's input has no producer, it's an external file."""
    external = tmp_path / "external.wav"
    external.write_text("audio")
    out = tmp_path / "out.txt"

    pl = Pipeline()
    pl.add(
        Task(
            name="t",
            fn=functools.partial(_touch, out, "ok"),
            inputs=(external,),
            outputs=(out,),
        )
    )
    pl.register_target("t", out)
    rc = pl.run("t")
    assert rc == 0
    assert out.read_text() == "ok"


def test_parallel_fanout_writes_all_outputs(tmp_path: Path) -> None:
    """All parallel-group tasks should run; outputs must exist after."""
    n = 6
    outputs = [tmp_path / f"f{i}.txt" for i in range(n)]
    pl = Pipeline()
    for i, out in enumerate(outputs):
        pl.add(
            Task(
                name=f"extract:{i}",
                fn=functools.partial(_touch, out, f"data-{i}"),
                outputs=(out,),
                parallel_group="features",
            )
        )

    # The "features" target points at the last output, but tasks have no
    # cross-dependencies, so we use a sentinel that depends on all of them.
    sentinel = tmp_path / "sentinel.txt"
    pl.add(
        Task(
            name="sentinel",
            fn=functools.partial(_touch, sentinel, "done"),
            inputs=tuple(outputs),
            outputs=(sentinel,),
        )
    )
    pl.register_target("features", sentinel)

    rc = pl.run("features", jobs=4)
    assert rc == 0
    for i, out in enumerate(outputs):
        assert out.read_text() == f"data-{i}"
    assert sentinel.read_text() == "done"


def test_staleness_propagates_to_downstream(tmp_path: Path) -> None:
    """If A is stale and B depends on A, B is stale even if B's outputs are
    currently newer than B's existing inputs."""
    a = tmp_path / "a.txt"
    b = tmp_path / "b.txt"
    c = tmp_path / "c.txt"

    # b.txt exists and is newer than a (a is missing); c.txt is also there.
    b.write_text("old-b")
    c.write_text("old-c")
    # a is missing, so A is stale; B will rerun because A reruns;
    # C will rerun because B reruns.

    ran: list[str] = []

    def record(name: str, out: Path) -> None:
        ran.append(name)
        out.write_text(name)

    pl = Pipeline()
    pl.add(Task("A", functools.partial(record, "A", a), outputs=(a,)))
    pl.add(Task("B", functools.partial(record, "B", b), inputs=(a,), outputs=(b,)))
    pl.add(Task("C", functools.partial(record, "C", c), inputs=(b,), outputs=(c,)))
    pl.register_target("C", c)

    plan = pl.plan("C")
    assert all(e.stale for e in plan), [e.task.name + ":" + e.reason for e in plan]
    rc = pl.run("C")
    assert rc == 0
    assert ran == ["A", "B", "C"]


def test_force_from_path_target_works(tmp_path: Path) -> None:
    """Resolving a target by its output path (not a registered name) works."""
    out = tmp_path / "out.txt"
    pl = Pipeline()
    pl.add(Task(name="t", fn=functools.partial(_touch, out, "ok"), outputs=(out,)))
    rc = pl.run(out)
    assert rc == 0
    assert out.read_text() == "ok"
