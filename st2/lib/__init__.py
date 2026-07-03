"""ST2 library API.

This module exposes the core functionality. CLI and web are thin wrappers.
All public functions should return JSON-serializable data structures.

For most uses, prefer ``st2.api`` which re-exports everything from here
and adds step functions for training workflows.

Example::

    from st2.api import (
        setup_project,
        validate_project,
        create_model,
        ST2Config,
        ConfigManager,
        Dictionary,
        Phoneset,
    )

Low-level C bindings are available via::

    from st2.lib._st2c import get_ffi, get_lib
    lib = get_lib()  # Direct C function access
    ffi = get_ffi()  # cffi FFI instance
"""

# Don't import _st2c eagerly - it requires the C library to be built
# Import directly: from st2.lib._st2c import get_ffi, get_lib

# Project setup and validation
# Configuration
from st2.lib.compare import (
    CompareResult,
    ComponentCompare,
    ModelCompareResult,
    compare_auto,
    compare_features,
    compare_gaussians,
    compare_gaussians_detailed,
    compare_mixw,
    compare_models,
    compare_senone_sets,
    compare_tmat,
    load_senones,
    load_senones_from_model,
)
from st2.lib.config import (
    AudioConfig,
    ConfigManager,
    FeatureConfig,
    ST2Config,
    TrainingConfig,
    get_feature_dir_name,
    get_user_config,
)

# Data structures
from st2.lib.dictionary import Dictionary

# File type detection and comparison
from st2.lib.filetypes import (
    FileType,
    assert_file_type,
    describe_file,
    detect_file_type,
    validate_file_type,
)

# Model classes
from st2.lib.model import (
    CDModel,
    CIModel,
    Model,
    create_model,
    get_model_class,
)

# Path discovery
from st2.lib.paths import ST2Paths, get_bin_dir, get_include_dir, get_lib_path, get_paths
from st2.lib.phoneset import Phoneset
from st2.lib.setup import setup_project

# Similarity metrics for Gaussian/senone comparison
from st2.lib.similarity import (
    GaussianState,
    Senone,
    bhattacharyya_distance,
    compare_senones,
    compare_states,
    cosine_similarity,
    euclidean_distance,
    kl_divergence,
    mahalanobis_distance,
    symmetric_kl_divergence,
)
from st2.lib.transcription import get_fileids, parse_transcription_file
from st2.lib.validate import ValidationReport, validate_project

__all__: list[str] = [
    # Project setup
    "setup_project",
    "validate_project",
    "ValidationReport",
    # Configuration
    "ST2Config",
    "AudioConfig",
    "FeatureConfig",
    "TrainingConfig",
    "ConfigManager",
    "get_user_config",
    "get_feature_dir_name",
    # Data structures
    "Dictionary",
    "Phoneset",
    "get_fileids",
    "parse_transcription_file",
    # Models
    "Model",
    "CIModel",
    "CDModel",
    "create_model",
    "get_model_class",
    # Paths
    "ST2Paths",
    "get_paths",
    "get_bin_dir",
    "get_lib_path",
    "get_include_dir",
    # File types
    "FileType",
    "detect_file_type",
    "describe_file",
    "validate_file_type",
    "assert_file_type",
    # Comparison
    "CompareResult",
    "ComponentCompare",
    "ModelCompareResult",
    "compare_auto",
    "compare_features",
    "compare_gaussians",
    "compare_gaussians_detailed",
    "compare_senone_sets",
    "compare_mixw",
    "compare_tmat",
    "compare_models",
    "load_senones",
    "load_senones_from_model",
    # Similarity metrics
    "GaussianState",
    "Senone",
    "bhattacharyya_distance",
    "compare_senones",
    "compare_states",
    "cosine_similarity",
    "euclidean_distance",
    "kl_divergence",
    "mahalanobis_distance",
    "symmetric_kl_divergence",
]
