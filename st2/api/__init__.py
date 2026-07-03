"""ST2 public API.

This is the recommended entry point for using ST2 programmatically.
CLI and web clients should call into this API.

All public functions return JSON-serializable data structures.

Example::

    from st2.api import (
        # Project setup
        setup_project,
        validate_project,
        ValidationReport,
        # Configuration
        ST2Config,
        ConfigManager,
        # Data structures
        Dictionary,
        Phoneset,
        # Models
        create_model,
        CIModel,
        CDModel,
        # Training steps
        run_step_ci_hmm,
    )
"""

from st2.api.steps import (
    run_step_cd_hmm_untied,
    run_step_ci_hmm,
    run_step_features,
    step_cd_hmm_untied,
    step_ci_hmm,
    step_features,
)

# Re-export lib API
from st2.lib import (
    AudioConfig,
    CDModel,
    CIModel,
    ConfigManager,
    # Data structures
    Dictionary,
    FeatureConfig,
    # Models
    Model,
    Phoneset,
    # Configuration
    ST2Config,
    TrainingConfig,
    create_model,
    get_feature_dir_name,
    get_fileids,
    get_model_class,
    get_user_config,
    parse_transcription_file,
    # Project setup
    setup_project,
    validate_project,
)
from st2.lib.validate import ValidationReport

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
    # Steps
    "step_features",
    "step_ci_hmm",
    "step_cd_hmm_untied",
    "run_step_features",
    "run_step_ci_hmm",
    "run_step_cd_hmm_untied",
]
