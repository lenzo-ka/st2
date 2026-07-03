"""ST2 Configuration System.

Three-tier configuration:

1. User (~/.st2/config.yaml) - Global defaults
2. Project (project/etc/config.yaml) - Shared across experiments
3. Experiment (project/experiments/{name}/config.yaml) - Experiment-specific

Example::

    from st2.lib.config import (
        ST2Config,
        ConfigManager,
        get_user_config,
        get_feature_dir_name,
    )

    # Load full config with merging
    config = ConfigManager.load_full_config(project_dir, experiment="baseline")

    # Access config values
    print(config.audio.sample_rate)
    print(config.features.num_ceps)

    # Get feature directory name
    feature_dir = get_feature_dir_name(config.audio, config.features)
    # -> "16khz_13cep_1s_c_d_dd_a1b2c3d4"
"""

from typing import TypedDict

# Main config model
# Feature ID generation
from st2.lib.config.feature_id import (
    get_feature_dir_name,
    get_feature_hash,
    get_feature_id,
    get_full_feature_dim,
)

# Config manager
from st2.lib.config.manager import ConfigManager
from st2.lib.config.models import (
    AudioConfig,
    CDConfig,
    CDTiedConfig,
    CDUntiedConfig,
    CITrainingConfig,
    CorpusConfig,
    DecisionTreeConfig,
    DictionaryConfig,
    FeatureConfig,
    GaussianIncrementConfig,
    ParallelConfig,
    SplitConfig,
    ST2Config,
    TrainingConfig,
)

# Schema introspection
from st2.lib.config.schema import (
    ParameterInfo,
    generate_markdown_docs,
    generate_rst_docs,
    get_parameter,
    get_schema,
    list_parameters,
)

# User config
from st2.lib.config.user import (
    JsonOutputConfig,
    ST2UserConfig,
    UserDefaults,
    get_user_config,
)


class FeatParams(TypedDict):
    """Schema for DEFAULT_FEAT_PARAMS; per-key concrete types enable
    type-correct lookups without casts."""

    samprate: int
    nfilt: int
    nfft: int
    lowerf: float
    upperf: float
    ncep: int
    alpha: float
    lifter: int
    feat_type: str


# Default feature parameters (derived from FeatureConfig/AudioConfig defaults).
# Use this constant instead of duplicating defaults across modules.
DEFAULT_FEAT_PARAMS: FeatParams = {
    "samprate": 16000,
    "nfilt": 40,
    "nfft": 512,
    "lowerf": 130.0,
    "upperf": 6800.0,
    "ncep": 13,
    "alpha": 0.97,
    "lifter": 22,
    "feat_type": "1s_c_d_dd",
}

__all__ = [
    # Constants
    "DEFAULT_FEAT_PARAMS",
    "FeatParams",
    # Main config
    "ST2Config",
    "AudioConfig",
    "FeatureConfig",
    "TrainingConfig",
    "CITrainingConfig",
    "CDConfig",
    "CDUntiedConfig",
    "CDTiedConfig",
    "GaussianIncrementConfig",
    "DecisionTreeConfig",
    "DictionaryConfig",
    "CorpusConfig",
    "SplitConfig",
    "ParallelConfig",
    # User config
    "ST2UserConfig",
    "UserDefaults",
    "JsonOutputConfig",
    "get_user_config",
    # Manager
    "ConfigManager",
    # Feature ID
    "get_feature_id",
    "get_feature_hash",
    "get_feature_dir_name",
    "get_full_feature_dim",
    # Schema introspection
    "get_schema",
    "list_parameters",
    "get_parameter",
    "generate_markdown_docs",
    "generate_rst_docs",
    "ParameterInfo",
]
