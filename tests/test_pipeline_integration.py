"""Integration tests for full CI model building pipeline.

Tests both Python and C backends, profiling each step.
Uses CMU Arctic SLT corpus as test data.
"""

from __future__ import annotations

import logging
import os
import shutil
from pathlib import Path
from typing import TYPE_CHECKING

import pytest

from st2.lib.backend import Backend, StatsTracker

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)

# Path to test project (set via ST2_TEST_PROJECT environment variable)
TEST_PROJECT_PATH = Path(os.environ.get("ST2_TEST_PROJECT", ""))


def _project_exists() -> bool:
    """Check if test project exists with required files."""
    if not TEST_PROJECT_PATH or not TEST_PROJECT_PATH.exists():
        return False
    required = [
        "shared/phoneset.txt",
        "shared/dictionary.dict",
    ]
    return all((TEST_PROJECT_PATH / p).exists() for p in required)


# Skip all tests if project doesn't exist
pytestmark = pytest.mark.skipif(
    not _project_exists(),
    reason=f"Test project not found at {TEST_PROJECT_PATH}",
)


@pytest.fixture(scope="module")
def project_dir() -> Path:
    """Return test project directory."""
    return TEST_PROJECT_PATH


@pytest.fixture(scope="module")
def stats_tracker(tmp_path_factory: pytest.TempPathFactory) -> StatsTracker:
    """Create a stats tracker for the test session."""
    stats_file = tmp_path_factory.mktemp("stats") / "pipeline_stats.json"
    return StatsTracker(stats_file)


@pytest.fixture(scope="module")
def work_dir(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """Create a temporary work directory for test outputs."""
    return tmp_path_factory.mktemp("pipeline_test")


class TestFeatureExtraction:
    """Test feature extraction step."""

    def test_python_feature_extraction(
        self,
        project_dir: Path,
        stats_tracker: StatsTracker,
        work_dir: Path,
    ) -> None:
        """Test feature extraction via Python/CFFI."""
        from st2.lib.backend import profile_execution
        from st2.lib.features import extract_features, read_sphinx_mfc

        # Find audio files
        audio_dir = project_dir / "audio"
        if not audio_dir.exists():
            pytest.skip("Audio directory not found")

        audio_files = list(audio_dir.glob("*.wav"))[:5]
        if not audio_files:
            pytest.skip("No audio files found")

        output_dir = work_dir / "features_python"
        output_dir.mkdir(parents=True, exist_ok=True)

        n_frames = 0

        with profile_execution(
            "feature_extraction",
            Backend.PYTHON,
            len(audio_files),
            stats_tracker,
            {"n_files": len(audio_files)},
        ):
            for audio_file in audio_files:
                output_file = output_dir / f"{audio_file.stem}.mfc"
                extract_features(audio_file, output_file)
                # Count frames for throughput
                feats = read_sphinx_mfc(output_file)
                n_frames += feats.shape[0]

        logger.info("Python feature extraction: %d files, %d frames", len(audio_files), n_frames)
        assert (output_dir / f"{audio_files[0].stem}.mfc").exists()

    def test_c_feature_extraction(
        self,
        project_dir: Path,
        stats_tracker: StatsTracker,
        work_dir: Path,
    ) -> None:
        """Test feature extraction via C binary (sphinx_fe)."""
        from st2.lib.backend import check_binary, profile_execution, run_binary

        # Find sphinx_fe binary
        sphinx_fe_paths = [
            Path("/usr/local/libexec/st2c/sphinx_fe"),
            Path("/usr/local/bin/sphinx_fe"),
            Path("/opt/local/bin/sphinx_fe"),
        ]
        sphinx_fe = None
        for p in sphinx_fe_paths:
            if check_binary(p):
                sphinx_fe = p
                break

        if sphinx_fe is None:
            pytest.skip("sphinx_fe binary not found")

        # Find audio files
        audio_dir = project_dir / "audio"
        if not audio_dir.exists():
            pytest.skip("Audio directory not found")

        audio_files = list(audio_dir.glob("*.wav"))[:5]
        if not audio_files:
            pytest.skip("No audio files found")

        output_dir = work_dir / "features_c"
        output_dir.mkdir(parents=True, exist_ok=True)

        with profile_execution(
            "feature_extraction",
            Backend.C,
            len(audio_files),
            stats_tracker,
            {"n_files": len(audio_files)},
        ):
            for audio_file in audio_files:
                output_file = output_dir / f"{audio_file.stem}.mfc"
                run_binary(
                    sphinx_fe,
                    [
                        "-i",
                        str(audio_file),
                        "-o",
                        str(output_file),
                        "-samprate",
                        "16000",
                        "-nfilt",
                        "40",
                        "-nfft",
                        "512",
                        "-lowerf",
                        "130",
                        "-upperf",
                        "6800",
                        "-ncep",
                        "13",
                        "-alpha",
                        "0.97",
                        "-dither",
                        "yes",
                    ],
                )

        logger.info("C feature extraction: %d files", len(audio_files))
        assert (output_dir / f"{audio_files[0].stem}.mfc").exists()


class TestFlatModelInit:
    """Test flat model initialization step."""

    def test_python_flat_init(
        self,
        project_dir: Path,
        stats_tracker: StatsTracker,
        work_dir: Path,
    ) -> None:
        """Test flat model init via Python."""
        from st2.lib.backend import profile_execution
        from st2.lib.flat import init_flat_model
        from st2.lib.phoneset import Phoneset

        phoneset = Phoneset.from_file(project_dir / "shared/phoneset.txt")
        phones = list(phoneset.phones())

        output_dir = work_dir / "flat_python"

        with profile_execution(
            "flat_init",
            Backend.PYTHON,
            len(phones),
            stats_tracker,
            {"n_phones": len(phones)},
        ):
            init_flat_model(
                phones=phones,
                output_dir=output_dir,
                n_density=1,
                n_state=3,
            )

        # Verify outputs
        assert (output_dir / "mdef").exists()
        assert (output_dir / "means").exists()
        assert (output_dir / "variances").exists()
        assert (output_dir / "mixture_weights").exists()
        assert (output_dir / "transition_matrices").exists()

    def test_c_flat_init(
        self,
        project_dir: Path,
        stats_tracker: StatsTracker,
        work_dir: Path,
    ) -> None:
        """Test flat model init via C binary (mk_flat)."""
        from st2.lib.backend import check_binary, profile_execution, run_binary

        # Find mk_flat binary
        mk_flat_paths = [
            Path("/usr/local/libexec/st2c/mk_flat"),
            Path("/usr/local/bin/mk_flat"),
        ]
        mk_flat = None
        for p in mk_flat_paths:
            if check_binary(p):
                mk_flat = p
                break

        if mk_flat is None:
            pytest.skip("mk_flat binary not found")

        # Need an mdef file first
        mdef_path = work_dir / "flat_python" / "mdef"
        if not mdef_path.exists():
            pytest.skip("Need Python flat_init to run first for mdef")

        output_dir = work_dir / "flat_c"
        output_dir.mkdir(parents=True, exist_ok=True)

        # Copy mdef
        shutil.copy(mdef_path, output_dir / "mdef")

        from st2.lib.phoneset import Phoneset

        phoneset = Phoneset.from_file(project_dir / "shared/phoneset.txt")

        with profile_execution(
            "flat_init",
            Backend.C,
            len(phoneset),
            stats_tracker,
            {"n_phones": len(phoneset)},
        ):
            run_binary(
                mk_flat,
                [
                    "-moddeffn",
                    str(output_dir / "mdef"),
                    "-topo",
                    "0.5 0.5 0.5 0.5 0.5 0.5",
                    "-mixwfn",
                    str(output_dir / "mixture_weights"),
                    "-tmatfn",
                    str(output_dir / "transition_matrices"),
                    "-nstream",
                    "1",
                    "-ndensity",
                    "1",
                ],
            )

        assert (output_dir / "mixture_weights").exists()
        assert (output_dir / "transition_matrices").exists()


class TestBWTraining:
    """Test Baum-Welch training step."""

    @pytest.fixture
    def model_dir(self, project_dir: Path) -> Path:
        """Get path to flat model for BW training."""
        model_dir = (
            project_dir
            / "experiments"
            / "default"
            / "models"
            / "ci"
            / "baseline"
            / "model"
            / "flat"
        )
        if not model_dir.exists():
            pytest.skip("Flat model not found - run flat init first")
        return model_dir

    @pytest.fixture
    def feature_dir(self, project_dir: Path) -> Path:
        """Get path to features."""
        # Find feature directory
        feat_base = project_dir / "shared" / "features"
        if not feat_base.exists():
            pytest.skip("Features not found")
        feat_dirs = list(feat_base.iterdir())
        if not feat_dirs:
            pytest.skip("No feature directories found")
        return feat_dirs[0]

    # Note: the Python BW path is the CFFI BWTrainer, exercised directly by
    # tests/test_st2c.py::test_st2_bw_init / test_st2_bw_process_utt in the
    # normal (non-integration) suite. The former empty-bodied,
    # unconditionally-skipped test_python_bw_iteration placeholder here was
    # removed as it asserted nothing.

    def test_c_bw_iteration(
        self,
        project_dir: Path,
        model_dir: Path,
        feature_dir: Path,
        stats_tracker: StatsTracker,
        work_dir: Path,
    ) -> None:
        """Test one BW iteration via C binary (bw)."""
        from st2.lib.backend import check_binary, profile_execution, run_binary

        # Find bw binary
        bw_paths = [
            Path("/usr/local/libexec/st2c/bw"),
            Path("/usr/local/bin/bw"),
        ]
        bw = None
        for p in bw_paths:
            if check_binary(p):
                bw = p
                break

        if bw is None:
            pytest.skip("bw binary not found")

        exp_dir = project_dir / "experiments" / "default"

        # Get frame count for throughput
        train_list = list((exp_dir / "etc/train.fileids").read_text().strip().split("\n"))[:10]

        from st2.lib.features import read_sphinx_mfc

        n_frames = 0
        for utt_id in train_list:
            mfc_file = feature_dir / f"{utt_id}.mfc"
            if mfc_file.exists():
                feats = read_sphinx_mfc(mfc_file)
                n_frames += feats.shape[0]

        output_dir = work_dir / "bw_c"
        output_dir.mkdir(parents=True, exist_ok=True)

        # Create control file
        ctl_file = output_dir / "train.ctl"
        ctl_file.write_text("\n".join(train_list))

        # Create transcript file in bw format
        trans_file = exp_dir / "etc/train.transcription"

        with profile_execution(
            "bw_iteration",
            Backend.C,
            n_frames,
            stats_tracker,
            {"n_utterances": len(train_list), "n_frames": n_frames},
        ):
            # A failure of the bw binary is a real defect, not a reason to
            # skip: let run_binary raise so the test fails. (The only
            # legitimate skip — bw binary absent — is handled above.)
            run_binary(
                bw,
                [
                    "-moddeffn",
                    str(model_dir / "mdef"),
                    "-ts2cbfn",
                    ".cont.",
                    "-feat",
                    "1s_c_d_dd",
                    "-cmn",
                    "current",
                    "-agc",
                    "none",
                    "-dictfn",
                    str(project_dir / "shared/dictionary.dict"),
                    "-fdictfn",
                    str(project_dir / "shared/filler.dict"),
                    "-ctlfn",
                    str(ctl_file),
                    "-cepdir",
                    str(feature_dir),
                    "-cepext",
                    ".mfc",
                    "-lsnfn",
                    str(trans_file),
                    "-accumdir",
                    str(output_dir),
                    "-meanfn",
                    str(model_dir / "means"),
                    "-varfn",
                    str(model_dir / "variances"),
                    "-mixwfn",
                    str(model_dir / "mixture_weights"),
                    "-tmatfn",
                    str(model_dir / "transition_matrices"),
                    "-timing",
                    "no",
                ],
            )

        # BW must actually have produced accumulator files (bw writes
        # gauden_counts / mixw_counts / tmat_counts into -accumdir; see
        # st2/lib/delint.py which consumes mixw_counts).
        produced = {f.name for f in output_dir.iterdir()}
        assert produced & {
            "gauden_counts",
            "mixw_counts",
            "tmat_counts",
        }, f"bw produced no accumulator files in {output_dir}: {sorted(produced)}"

        logger.info("C BW iteration: %d utts, %d frames", len(train_list), n_frames)


class TestPipelineComparison:
    """Compare full pipeline between backends."""

    def test_print_stats_summary(self, stats_tracker: StatsTracker) -> None:
        """Print summary of all profiled operations."""
        summary = stats_tracker.summary()
        logger.info("\n=== Pipeline Performance Summary ===\n%s", summary)
        print(f"\n=== Pipeline Performance Summary ===\n{summary}")

        # Also print recommendations
        for op in ["feature_extraction", "flat_init", "bw_iteration"]:
            rec = stats_tracker.recommended_backend(op)
            print(f"Recommended backend for {op}: {rec.value}")
