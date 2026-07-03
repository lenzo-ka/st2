"""End-to-end training smoke test on a tiny real corpus.

Runs the actual training pipeline — feature extraction → flat init → ci-1g
Baum-Welch — on a 10-utterance CMU ARCTIC slice (tests/fixtures/mini_arctic)
and asserts it produces a valid, finite CI acoustic model.

This is the safety net Phase 1 exists to provide: a PR that breaks BW
training, flat init, or feature extraction turns this test red. Everything
here runs in-process against libst2c via CFFI (no CLI binaries needed), so
the only requirement is a built C library.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np

from tests.clib import requires_c_library

FIXTURE = Path(__file__).parent / "fixtures" / "mini_arctic"


@requires_c_library
def test_build_ci_1g_produces_finite_model(tmp_path: Path) -> None:
    """features → flat → ci-1g yields a finite, converged CI model."""
    from st2.lib.pipeline import PipelineContext
    from st2.lib.pipeline.tasks import build_pipeline
    from st2.lib.setup import setup_project

    project_dir = tmp_path / "proj"

    setup_project(
        project_dir,
        transcription_path=FIXTURE / "transcription.txt",
        audio_path=FIXTURE / "wav",
        dictionary_path=FIXTURE / "dictionary.dict",
        phoneset_path=FIXTURE / "phoneset.txt",
        filler_dict_path=FIXTURE / "filler.dict",
    )

    ctx = PipelineContext.from_config(project_dir)
    rc = build_pipeline(ctx).run("ci-1g", jobs=2)
    assert rc == 0, "pipeline run of ci-1g failed"

    model_dir = ctx.model_dir("ci-1g")
    for name in ("mdef", "means", "variances", "mixture_weights", "transition_matrices"):
        assert (model_dir / name).exists(), f"missing model file: {name}"

    # Every model parameter must be finite. Unobserved/degenerate states are
    # the classic way BW produces NaN/inf; this is the assertion that catches
    # a broken trainer or a phoneset with untrained phones.
    from st2.lib import _st2c

    means = _st2c.read_gau(str(model_dir / "means"))[0]
    variances = _st2c.read_gau(str(model_dir / "variances"))[0]
    mixw = _st2c.read_mixw(str(model_dir / "mixture_weights"))[0]

    assert np.isfinite(means).all(), "non-finite values in means"
    assert np.isfinite(variances).all(), "non-finite values in variances"
    assert np.isfinite(mixw).all(), "non-finite values in mixture_weights"
    # Variances must stay positive (variance flooring); a non-positive
    # variance would make the Gaussians degenerate at decode time.
    assert (variances > 0).all(), "non-positive variances"


@requires_c_library
def test_features_extracted_for_every_utterance(tmp_path: Path) -> None:
    """Feature extraction fans out to one .mfc per fixture utterance."""
    from st2.lib.pipeline import PipelineContext
    from st2.lib.pipeline.tasks import build_pipeline
    from st2.lib.setup import setup_project

    project_dir = tmp_path / "proj"
    setup_project(
        project_dir,
        transcription_path=FIXTURE / "transcription.txt",
        audio_path=FIXTURE / "wav",
        dictionary_path=FIXTURE / "dictionary.dict",
        phoneset_path=FIXTURE / "phoneset.txt",
        filler_dict_path=FIXTURE / "filler.dict",
    )

    ctx = PipelineContext.from_config(project_dir)
    rc = build_pipeline(ctx).run("features", jobs=2)
    assert rc == 0

    n_wav = len(list((FIXTURE / "wav").glob("*.wav")))
    mfcs = list(ctx.features_dir.glob("*.mfc"))
    assert len(mfcs) == n_wav, f"expected {n_wav} .mfc files, got {len(mfcs)}"
