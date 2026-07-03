"""CLI command for feature extraction.

Drives the pipeline runner's "features" target, which fans out one task per
fileid in `train.fileids` + `test.fileids` and runs them in a process pool.
"""

from __future__ import annotations

import argparse

from st2.cli.base import CommandContext, CommandResult, ProjectCommand
from st2.lib.pipeline import PipelineContext, UnknownTargetError
from st2.lib.pipeline.tasks import build_pipeline


class FeaturesCommand(ProjectCommand):
    """Extract acoustic features from audio files."""

    name = "features"
    help = "Extract acoustic features from audio files"
    description = (
        "Extract MFCC features from audio files listed in "
        "experiments/{experiment}/etc/{train,test}.fileids."
    )

    def add_arguments(self, parser: argparse.ArgumentParser) -> None:
        parser.add_argument(
            "-c",
            "--config",
            type=str,
            default="default",
            dest="config_name",
            help="Named config from etc/configs.yaml (default: default)",
        )
        parser.add_argument(
            "-j",
            "--jobs",
            type=int,
            default=1,
            help="Number of parallel worker processes (default: 1)",
        )
        parser.add_argument(
            "--force",
            action="store_true",
            help="Re-extract all features, even if up to date",
        )

    def execute(self, ctx: CommandContext) -> CommandResult:
        try:
            pipeline_ctx = PipelineContext.from_config(
                ctx.project_dir,
                experiment=ctx.experiment,
                config_name=ctx.args.config_name,
            )
        except ValueError as exc:
            return CommandResult.fail(str(exc))

        fileids = pipeline_ctx.all_fileids()
        if not fileids and not ctx.dry_run:
            return CommandResult.fail(
                "No fileids found. Run 'st2 split' first to create train/test fileids."
            )

        ctx.log_action("Extract features", str(pipeline_ctx.features_dir))
        ctx.log(f"  Audio:  {pipeline_ctx.audio_dir}")
        ctx.log(f"  Output: {pipeline_ctx.features_dir}")
        ctx.log(f"  Files:  {len(fileids)}")
        ctx.log(f"  Jobs:   {ctx.args.jobs}")

        pipeline = build_pipeline(pipeline_ctx)
        try:
            rc = pipeline.run(
                "features",
                dry_run=ctx.dry_run,
                force=ctx.args.force,
                jobs=ctx.args.jobs,
            )
        except UnknownTargetError as exc:
            return CommandResult.fail(f"unknown target: {exc}")

        if rc == 0:
            return CommandResult.ok()
        return CommandResult.fail(f"feature extraction failed (rc={rc})", exit_code=rc)


features_command = FeaturesCommand()
