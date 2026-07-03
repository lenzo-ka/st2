"""Setup command for ST2."""

from __future__ import annotations

import argparse
from pathlib import Path

from st2.cli.base import Command, CommandContext, CommandResult


class SetupCommand(Command):
    """Set up a new ST2 project."""

    name = "setup"
    help = "Set up a new ST2 project"
    description = "Initialize a new ST2 project with required files and directory structure"
    needs_project_dir = False  # We handle project_dir specially as positional arg
    needs_experiment = False

    def add_arguments(self, parser: argparse.ArgumentParser) -> None:
        """Add setup-specific arguments."""
        parser.add_argument(
            "project_dir",
            nargs="?",
            type=str,
            help="Project directory (default: current directory)",
        )
        parser.add_argument(
            "--transcription",
            type=str,
            help="Path to transcription file (fileid + words)",
        )
        parser.add_argument(
            "--audio",
            type=str,
            help="Path to audio files directory or file",
        )
        parser.add_argument(
            "--dictionary",
            type=str,
            help="Path to pronunciation dictionary file",
        )
        parser.add_argument(
            "--phoneset",
            type=str,
            help="Path to phoneset file (or extract from dictionary)",
        )
        parser.add_argument(
            "--filler-dict",
            type=str,
            help="Path to filler dictionary (optional)",
        )
        parser.add_argument(
            "--config",
            type=str,
            help="Path to config file (or create default)",
        )
        parser.add_argument(
            "--link",
            action="store_true",
            help="Symlink audio directory instead of copying (only if --audio is provided)",
        )
        parser.add_argument(
            "--clobber",
            action="store_true",
            help="Overwrite existing files (default: skip existing files)",
        )
        parser.add_argument(
            "--validate",
            action="store_true",
            help="Run validation after setup",
        )

    def execute(self, ctx: CommandContext) -> CommandResult:
        """Execute setup command.

        Single code path - ctx methods emit shell in dry-run, execute otherwise.
        """
        # Resolve project directory
        if ctx.args.project_dir:
            project_dir = Path(ctx.args.project_dir).resolve()
        else:
            project_dir = Path.cwd()

        # Resolve input paths
        transcription_path = (
            Path(ctx.args.transcription).resolve() if ctx.args.transcription else None
        )
        audio_path = Path(ctx.args.audio).resolve() if ctx.args.audio else None
        dictionary_path = Path(ctx.args.dictionary).resolve() if ctx.args.dictionary else None
        phoneset_path = Path(ctx.args.phoneset).resolve() if ctx.args.phoneset else None
        filler_dict_path = Path(ctx.args.filler_dict).resolve() if ctx.args.filler_dict else None

        # Single code path - these emit shell in dry-run, execute otherwise
        ctx.comment(f"Setup project: {project_dir}")
        ctx.blank()

        # Create directory structure
        ctx.comment("Create directory structure")
        ctx.mkdir(project_dir)
        for subdir in ["etc", "audio", "shared", "shared/features", "experiments"]:
            ctx.mkdir(project_dir / subdir)
        ctx.blank()

        # Copy transcription
        if transcription_path:
            ctx.comment("Copy transcription file")
            ctx.copy(transcription_path, project_dir / "etc" / "all.transcription")
            ctx.blank()

        # Handle audio
        if audio_path:
            ctx.comment("Set up audio files")
            if ctx.args.link:
                ctx.symlink(audio_path, project_dir / "audio")
            elif audio_path.is_dir():
                ctx.copy_tree(audio_path, project_dir / "audio")
            else:
                ctx.copy(audio_path, project_dir / "audio" / audio_path.name)
            ctx.blank()

        # Copy dictionary
        if dictionary_path:
            ctx.comment("Copy dictionary")
            ctx.copy(dictionary_path, project_dir / "shared" / "dictionary.dict")
            ctx.blank()

        # Handle phoneset
        if phoneset_path:
            ctx.comment("Copy phoneset")
            ctx.copy(phoneset_path, project_dir / "shared" / "phoneset.txt")
            ctx.blank()
        elif dictionary_path:
            ctx.comment("Extract phoneset from dictionary")
            ctx.st2(
                "phoneset",
                "--extract",
                str(dictionary_path),
                output=str(project_dir / "shared" / "phoneset.txt"),
            )
            ctx.blank()

        # Handle filler dictionary
        if filler_dict_path:
            ctx.comment("Copy filler dictionary")
            ctx.copy(filler_dict_path, project_dir / "shared" / "filler.dict")
        else:
            ctx.comment("Copy default filler dictionary")
            ctx.st2("data", "filler.dict", output=str(project_dir / "shared" / "filler.dict"))
        ctx.blank()

        # Initialize config
        ctx.comment("Initialize config")
        ctx.st2("config", "init", project_dir=str(project_dir))
        ctx.blank()

        # Validation
        if ctx.args.validate:
            ctx.comment("Validate project")
            ctx.st2("validate-project", str(project_dir))
            ctx.blank()

        ctx.comment("Done. To work in this project:")
        ctx.comment(f"  cd {project_dir}")

        return CommandResult.ok()


# Singleton instance for registration
setup_command = SetupCommand()
