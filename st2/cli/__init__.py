"""Command-line interface for ST2.

The CLI provides commands for the complete acoustic model training workflow:
- ``st2 setup`` - Initialize a new project
- ``st2 validate-project`` - Validate project structure
- ``st2 split`` - Split data into train/test sets
- ``st2 features`` - Extract acoustic features
- ``st2 flat`` - Initialize flat HMM models
- ``st2 ci`` - Train context-independent models
- ``st2 clean`` - Clean training outputs
- ``st2 config`` - Manage configuration
- ``st2 step`` - Run numbered training steps

All commands support ``--dry-run`` to preview actions without execution.
"""

from st2.cli.base import Command, CommandContext, CommandResult, ModelCommand, ProjectCommand
from st2.cli.cli import main

__all__ = [
    "main",
    "Command",
    "CommandContext",
    "CommandResult",
    "ModelCommand",
    "ProjectCommand",
]
