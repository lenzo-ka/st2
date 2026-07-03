"""Base model class and model implementations.

Each model type (CI, CD) is a class that knows about its own training process,
parameters, directory structure, and requirements.

Models provide metadata for the pipeline runner:
- File paths (inputs, outputs)
- Parameters (training settings)
- Dependencies (what stages must run first)
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

# Required model files (needed for training/BW)
MODEL_FILES_REQUIRED = ["mdef", "means", "variances", "mixture_weights", "transition_matrices"]

# Optional model files (for deployment/decoding)
MODEL_FILES_OPTIONAL = ["sendump", "feat.params", "noisedict"]

# All known model files
MODEL_FILES_ALL = MODEL_FILES_REQUIRED + MODEL_FILES_OPTIONAL

__all__ = [
    "MODEL_FILES_REQUIRED",
    "MODEL_FILES_OPTIONAL",
    "MODEL_FILES_ALL",
    "TrainingStage",
    "Model",
    "CIModel",
    "CDModel",
    "create_model",
    "get_model_class",
]


@dataclass
class TrainingStage:
    """Represents a training stage in the pipeline.

    Used to define the sequence of stages for a model type.
    """

    name: str
    description: str = ""
    script: str = ""
    inputs: dict[str, str] = field(default_factory=dict)
    outputs: dict[str, str] = field(default_factory=dict)
    params: dict[str, Any] = field(default_factory=dict)
    depends_on: list[str] = field(default_factory=list)


class Model(ABC):
    """Base class for acoustic models.

    Each model type (CI, CD) should inherit from this class and implement
    the abstract methods to define its specific behavior.
    """

    def __init__(self, config: str = "baseline") -> None:
        """Initialize model.

        Args:
            config: Model configuration name (e.g., "baseline", "1g", "lda")
        """
        self.config = config

    @property
    @abstractmethod
    def model_type(self) -> str:
        """Model type identifier (e.g., "ci", "cd")."""
        pass

    @property
    @abstractmethod
    def display_name(self) -> str:
        """Human-readable name for the model type."""
        pass

    @property
    @abstractmethod
    def default_topn(self) -> int:
        """Default top-n Gaussians for this model type."""
        pass

    def get_model_dir(self, experiment_dir: str | Path) -> Path:
        """Get the model directory for this model.

        Args:
            experiment_dir: Experiment directory path

        Returns:
            Path to model directory: {experiment_dir}/models/{model_type}/{config}/model/
        """
        experiment_dir = Path(experiment_dir)
        return experiment_dir / "models" / self.model_type / self.config / "model"

    def get_flat_dir(self, experiment_dir: str | Path) -> Path:
        """Get the flat model directory for this model."""
        return self.get_model_dir(experiment_dir) / "flat"

    def get_hmm_dir(self, experiment_dir: str | Path) -> Path:
        """Get the trained HMM model directory for this model."""
        return self.get_model_dir(experiment_dir) / "hmm"

    @abstractmethod
    def get_training_dependencies(self) -> list[str]:
        """Get list of dependencies required for training.

        Returns:
            List of dependency names (e.g., ["flat", "features", "dictionary", "split"])
        """
        pass

    @abstractmethod
    def get_default_training_params(self) -> dict[str, Any]:
        """Get default training parameters for this model type.

        Returns:
            Dictionary of parameter names to default values
        """
        pass

    def validate_training_params(self, params: dict[str, Any]) -> dict[str, Any]:
        """Validate and normalize training parameters.

        Args:
            params: Training parameters to validate

        Returns:
            Validated parameters with defaults filled in

        Raises:
            ValueError: If parameters are invalid
        """
        defaults = self.get_default_training_params()
        validated = defaults.copy()
        validated.update(params)
        return validated

    @abstractmethod
    def get_training_stages(
        self,
        project_dir: Path | str,
        experiment: str = "baseline",
        training_params: dict[str, Any] | None = None,
    ) -> list[TrainingStage]:
        """Get the sequence of training stages for this model.

        Returns a list of TrainingStage objects in execution order
        (e.g., 20.ci_hmm, 30.cd_hmm_untied).

        Args:
            project_dir: Project directory path
            experiment: Experiment name
            training_params: Optional training parameters

        Returns:
            List of TrainingStage objects in execution order
        """
        pass

    @classmethod
    @abstractmethod
    def from_string(cls, value: str) -> type[Model]:
        """Get model class from string identifier.

        Args:
            value: Model type string (e.g., "ci", "CD", "context-independent")

        Returns:
            Model class

        Raises:
            ValueError: If model type is unknown
        """
        pass


class CIModel(Model):
    """Context-Independent (monophone) acoustic model."""

    @property
    def model_type(self) -> str:
        return "ci"

    @property
    def display_name(self) -> str:
        return "Context-Independent"

    @property
    def default_topn(self) -> int:
        return 1

    def get_training_dependencies(self) -> list[str]:
        """Get list of dependencies required for CI model training.

        Returns:
            List of dependency names: ["flat", "features", "dictionary", "split"]
        """
        return ["flat", "features", "dictionary", "split"]

    def get_training_stages(
        self,
        project_dir: Path | str,
        experiment: str = "baseline",
        training_params: dict[str, Any] | None = None,
    ) -> list[TrainingStage]:
        """Get training stages for CI training.

        CI training runs Baum-Welch iterations to train context-independent models.

        Args:
            project_dir: Project directory path
            experiment: Experiment name
            training_params: Optional training parameters

        Returns:
            List of TrainingStage objects
        """
        if training_params is None:
            training_params = self.get_default_training_params()

        project_dir = Path(project_dir)
        experiment_dir = project_dir / "experiments" / experiment
        flat_dir = self.get_flat_dir(experiment_dir)
        hmm_dir = self.get_hmm_dir(experiment_dir)

        # CI HMM training (Baum-Welch)
        return [
            TrainingStage(
                name="ci_hmm",
                script="bw",  # Uses bw program with iterations
                inputs={
                    "flat_mdef": str(flat_dir / "mdef"),
                    "flat_means": str(flat_dir / "means"),
                    "flat_variances": str(flat_dir / "variances"),
                    "flat_mixture_weights": str(flat_dir / "mixture_weights"),
                    "flat_transition_matrices": str(flat_dir / "transition_matrices"),
                    "dictionary": str(project_dir / "shared" / "dictionary.dict"),
                    "train_fileids": str(experiment_dir / "etc" / "train.fileids"),
                    "train_transcription": str(experiment_dir / "etc" / "train.transcription"),
                    "features_dir": str(project_dir / "shared" / "features" / "default"),
                },
                outputs={
                    "hmm_mdef": str(hmm_dir / "mdef"),
                    "hmm_means": str(hmm_dir / "means"),
                    "hmm_variances": str(hmm_dir / "variances"),
                    "hmm_mixture_weights": str(hmm_dir / "mixture_weights"),
                    "hmm_transition_matrices": str(hmm_dir / "transition_matrices"),
                    "feat_params": str(hmm_dir / "feat.params"),
                },
                params={
                    "max_iterations": training_params.get("max_iterations", 10),
                    "min_iterations": training_params.get("min_iterations", 3),
                    "convergence_threshold": training_params.get("convergence_threshold", 0.001),
                    "topn": training_params.get("topn", 1),
                    "abeam": training_params.get("abeam", 1e-90),
                    "bbeam": training_params.get("bbeam", 1e-10),
                    "varfloor": training_params.get("varfloor", 0.0001),
                    "mixw_floor": training_params.get("mixw_floor", 0.00001),
                },
                description="Train context-independent HMM models using Baum-Welch",
            )
        ]

    def get_default_training_params(self) -> dict[str, Any]:
        """Get default training parameters for CI models.

        Returns:
            Dictionary of parameter names to default values for CI model training
        """
        return {
            "max_iterations": 10,
            "min_iterations": 3,
            "convergence_threshold": 0.001,
            "abeam": 1e-90,
            "bbeam": 1e-10,
            "topn": 1,
            "varfloor": 1e-4,
            "mixw_floor": 1e-8,
            "2passvar": False,  # First iteration uses False, subsequent use True
            "save_alignments": False,
            "gaussian_splitting": None,  # None = no splitting, or list like [1, 2, 4, 8]
            "n_iterations_after_split": 3,  # Iterations after each Gaussian split
        }

    @classmethod
    def from_string(cls, value: str) -> type[Model]:
        """Get model class from string identifier.

        Args:
            value: Model type string (e.g., "ci", "CD", "context-independent")

        Returns:
            Model class (CIModel)

        Raises:
            ValueError: If model type is unknown
        """
        value_lower = value.lower()
        if value_lower in ("ci", "context-independent", "monophone"):
            return cls
        raise ValueError(f"Unknown CI model type: {value}")


class CDModel(Model):
    """Context-Dependent (triphone) acoustic model."""

    @property
    def model_type(self) -> str:
        return "cd"

    @property
    def display_name(self) -> str:
        return "Context-Dependent"

    @property
    def default_topn(self) -> int:
        return 4

    def get_training_dependencies(self) -> list[str]:
        """Get list of dependencies required for CD model training.

        Returns:
            List of dependency names: ["ci", "features", "dictionary", "split"]
            Note: CD models depend on CI models, so "ci" is included
        """
        return ["ci", "features", "dictionary", "split"]

    def get_training_stages(
        self,
        project_dir: Path | str,
        experiment: str = "baseline",
        training_params: dict[str, Any] | None = None,
    ) -> list[TrainingStage]:
        """Get training stages for CD training.

        CD training includes:
        - cd_hmm_untied: Context-dependent untied models
        - build_trees: Decision tree building
        - prune_tree: State tying
        - cd_hmm_tied: Context-dependent tied models

        Args:
            project_dir: Project directory path
            experiment: Experiment name
            training_params: Optional training parameters

        Returns:
            List of TrainingStage objects
        """
        # TODO: Implement full CD training stages
        # For now, return placeholder
        return [
            TrainingStage(
                name="cd_hmm_untied",
                script="bw",
                inputs={},
                outputs={},
                params={},
                description="CD training (not yet implemented)",
            )
        ]

    def get_default_training_params(self) -> dict[str, Any]:
        """Get default training parameters for CD models.

        Returns:
            Dictionary of parameter names to default values for CD model training
        """
        return {
            "max_iterations": 10,
            "min_iterations": 3,
            "convergence_threshold": 0.001,
            "abeam": 1e-90,
            "bbeam": 1e-10,
            "topn": 4,
            "varfloor": 1e-4,
            "mixw_floor": 1e-8,
            "2passvar": False,
            "save_alignments": False,
            "gaussian_splitting": None,  # None = no splitting, or list like [1, 2, 4, 8]
            "n_iterations_after_split": 3,  # Iterations after each Gaussian split
        }

    @classmethod
    def from_string(cls, value: str) -> type[Model]:
        """Get model class from string identifier.

        Args:
            value: Model type string (e.g., "cd", "CD", "context-dependent")

        Returns:
            Model class (CDModel)

        Raises:
            ValueError: If model type is unknown
        """
        value_lower = value.lower()
        if value_lower in ("cd", "context-dependent", "triphone"):
            return cls
        raise ValueError(f"Unknown CD model type: {value}")


def get_model_class(model_type: str) -> type[Model]:
    """Get model class from model type string.

    Args:
        model_type: Model type identifier (e.g., "ci", "cd")

    Returns:
        Model class

    Raises:
        ValueError: If model type is unknown
    """
    value_lower = model_type.lower()

    # Try CI first
    try:
        return CIModel.from_string(value_lower)
    except ValueError:
        pass

    # Try CD
    try:
        return CDModel.from_string(value_lower)
    except ValueError:
        pass

    raise ValueError(
        f"Unknown model type: {model_type}. "
        f"Valid types: ci (Context-Independent), cd (Context-Dependent)"
    )


def create_model(model_type: str, config: str = "baseline") -> Model:
    """Create a model instance.

    Args:
        model_type: Model type identifier (e.g., "ci", "cd")
        config: Model configuration name (default: "baseline")

    Returns:
        Model instance of the specified type

    Raises:
        ValueError: If model type is unknown
    """
    model_class = get_model_class(model_type)
    return model_class(config=config)
