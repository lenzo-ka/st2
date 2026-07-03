"""Model packaging for distribution.

Creates distributable model packages compatible with PocketSphinx,
Sphinx3, and other Sphinx-based decoders.
"""

from __future__ import annotations

import logging
import shutil
from datetime import datetime
from pathlib import Path
from typing import Any

from st2.lib.config import DEFAULT_FEAT_PARAMS
from st2.lib.model import MODEL_FILES_REQUIRED

logger = logging.getLogger(__name__)

__all__ = ["package_model", "create_feat_params", "create_noisedict"]

# Shorthand for defaults
_D = DEFAULT_FEAT_PARAMS


def create_feat_params(
    output_path: Path,
    samprate: int | None = None,
    nfilt: int | None = None,
    nfft: int | None = None,
    lowerf: float | None = None,
    upperf: float | None = None,
    ncep: int | None = None,
    feat_type: str | None = None,
) -> Path:
    """Create feat.params file for Sphinx decoders.

    Args:
        output_path: Output file path
        samprate: Sampling rate in Hz (default from DEFAULT_FEAT_PARAMS)
        nfilt: Number of mel filters (default from DEFAULT_FEAT_PARAMS)
        nfft: FFT size (default from DEFAULT_FEAT_PARAMS)
        lowerf: Lower frequency bound (default from DEFAULT_FEAT_PARAMS)
        upperf: Upper frequency bound (default from DEFAULT_FEAT_PARAMS)
        ncep: Number of cepstral coefficients (default from DEFAULT_FEAT_PARAMS)
        feat_type: Feature type string (default from DEFAULT_FEAT_PARAMS)

    Returns:
        Path to created file
    """
    # Apply defaults from canonical source
    samprate = samprate if samprate is not None else _D["samprate"]
    nfilt = nfilt if nfilt is not None else _D["nfilt"]
    nfft = nfft if nfft is not None else _D["nfft"]
    lowerf = lowerf if lowerf is not None else _D["lowerf"]
    upperf = upperf if upperf is not None else _D["upperf"]
    ncep = ncep if ncep is not None else _D["ncep"]
    feat_type = feat_type if feat_type is not None else _D["feat_type"]

    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, "w") as f:
        f.write(f"-samprate {samprate}\n")
        f.write(f"-nfilt {nfilt}\n")
        f.write(f"-nfft {nfft}\n")
        f.write(f"-lowerf {lowerf}\n")
        f.write(f"-upperf {upperf}\n")
        f.write(f"-ncep {ncep}\n")
        f.write(f"-feat {feat_type}\n")
        # Additional params that decoders may need
        f.write("-transform dct\n")
        f.write("-lifter 0\n")
        f.write("-unit_area yes\n")
        f.write("-round_filters yes\n")
        f.write("-remove_dc yes\n")

    logger.info("Created feat.params: %s", output_path)
    return output_path


def create_noisedict(
    output_path: Path,
    filler_dict_path: Path | None = None,
) -> Path:
    """Create noisedict file for Sphinx decoders.

    This is the filler dictionary used during decoding.

    Args:
        output_path: Output file path
        filler_dict_path: Source filler dictionary (optional)

    Returns:
        Path to created file
    """
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    if filler_dict_path and Path(filler_dict_path).exists():
        # Copy existing filler dict
        shutil.copy(filler_dict_path, output_path)
    else:
        # Create minimal noisedict (matches st2/data/filler.dict)
        with open(output_path, "w") as f:
            f.write("<sil> SIL\n")
            f.write("<s> SIL\n")
            f.write("</s> SIL\n")

    logger.info("Created noisedict: %s", output_path)
    return output_path


def package_model(
    model_dir: Path,
    output_dir: Path,
    model_name: str | None = None,
    dictionary_path: Path | None = None,
    filler_dict_path: Path | None = None,
    feat_params: dict[str, Any] | None = None,
    include_dict: bool = True,
) -> dict[str, Path]:
    """Package a trained model for distribution.

    Creates a complete, self-contained model directory that can be
    used directly with PocketSphinx and other Sphinx decoders.

    Args:
        model_dir: Source model directory
        output_dir: Output directory for packaged model
        model_name: Name for the model (used in output path)
        dictionary_path: Path to pronunciation dictionary
        filler_dict_path: Path to filler dictionary
        feat_params: Feature parameters dict (samprate, nfilt, etc.)
        include_dict: Whether to include dictionary in package

    Returns:
        Dict mapping file types to output paths

    Example output structure::

        dist/models/my-model/
        ├── acoustic/
        │   ├── feat.params
        │   ├── mdef
        │   ├── means
        │   ├── variances
        │   ├── mixture_weights
        │   ├── transition_matrices
        │   └── noisedict
        ├── dict/
        │   ├── cmudict.dict
        │   └── filler.dict
        └── README.txt
    """
    model_dir = Path(model_dir)
    output_dir = Path(output_dir)

    if model_name:
        package_dir = output_dir / model_name
    else:
        package_dir = output_dir

    # Create directory structure
    acoustic_dir = package_dir / "acoustic"
    acoustic_dir.mkdir(parents=True, exist_ok=True)

    result: dict[str, Path] = {}

    # Copy acoustic model files
    for fname in MODEL_FILES_REQUIRED:
        src = model_dir / fname
        dst = acoustic_dir / fname
        if src.exists():
            shutil.copy(src, dst)
            result[fname] = dst
            logger.debug("Copied %s -> %s", src, dst)
        else:
            logger.warning("Model file not found: %s", src)

    # Create feat.params (defaults come from DEFAULT_FEAT_PARAMS)
    feat_params = feat_params or {}
    feat_path = create_feat_params(
        acoustic_dir / "feat.params",
        samprate=feat_params.get("samprate"),
        nfilt=feat_params.get("nfilt"),
        nfft=feat_params.get("nfft"),
        lowerf=feat_params.get("lowerf"),
        upperf=feat_params.get("upperf"),
        ncep=feat_params.get("ncep"),
        feat_type=feat_params.get("feat_type"),
    )
    result["feat_params"] = feat_path

    # Create noisedict
    noisedict_path = create_noisedict(
        acoustic_dir / "noisedict",
        filler_dict_path,
    )
    result["noisedict"] = noisedict_path

    # Copy dictionary files if requested
    if include_dict:
        dict_dir = package_dir / "dict"
        dict_dir.mkdir(parents=True, exist_ok=True)

        if dictionary_path and Path(dictionary_path).exists():
            dict_dst = dict_dir / "cmudict.dict"
            shutil.copy(dictionary_path, dict_dst)
            result["dictionary"] = dict_dst
            logger.debug("Copied dictionary: %s", dict_dst)

        if filler_dict_path and Path(filler_dict_path).exists():
            filler_dst = dict_dir / "filler.dict"
            shutil.copy(filler_dict_path, filler_dst)
            result["filler_dict"] = filler_dst
            logger.debug("Copied filler dict: %s", filler_dst)

    # Create README
    readme_path = package_dir / "README.txt"
    _create_readme(readme_path, model_name, feat_params)
    result["readme"] = readme_path

    logger.info("Packaged model to: %s", package_dir)
    return result


def _create_readme(
    output_path: Path,
    model_name: str | None,
    feat_params: dict[str, Any] | None,
) -> None:
    """Create README file for the model package."""
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    feat_params = feat_params or {}

    content = f"""ST2 Acoustic Model Package
==========================

Model: {model_name or "unnamed"}
Created: {now}
Generator: st2 (SphinxTrain 2)

Directory Structure
-------------------
acoustic/       - Acoustic model files for Sphinx decoders
  feat.params   - Feature extraction parameters
  mdef          - Model definition (phones, states, triphones)
  means         - Gaussian means
  variances     - Gaussian variances
  mixture_weights - Mixture weights
  transition_matrices - HMM state transition probabilities
  noisedict     - Filler/noise dictionary for decoding

dict/           - Dictionary files
  cmudict.dict  - Pronunciation dictionary
  filler.dict   - Filler word dictionary

Usage with PocketSphinx
-----------------------
Python:
    from pocketsphinx import Decoder

    config = Decoder.default_config()
    config.set_string('-hmm', '/path/to/{model_name or "model"}/acoustic')
    config.set_string('-dict', '/path/to/{model_name or "model"}/dict/cmudict.dict')
    decoder = Decoder(config)

Command line:
    pocketsphinx -hmm {model_name or "model"}/acoustic \\
                 -dict {model_name or "model"}/dict/cmudict.dict \\
                 -infile audio.wav

Feature Parameters
------------------
Sample rate: {feat_params.get("samprate", 16000)} Hz
Mel filters: {feat_params.get("nfilt", 40)}
FFT size: {feat_params.get("nfft", 512)}
Frequency range: {feat_params.get("lowerf", 130)}-{feat_params.get("upperf", 6800)} Hz
Cepstral coefficients: {feat_params.get("ncep", 13)}
Feature type: {feat_params.get("feat_type", "1s_c_d_dd")}

License
-------
See the project repository for license information.
"""
    with open(output_path, "w") as f:
        f.write(content)
