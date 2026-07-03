"""CLI command for CI model training."""

from __future__ import annotations

import argparse

from st2.cli.base import CommandContext, CommandResult, ModelCommand


class CICommand(ModelCommand):
    """Train Context-Independent (monophone) acoustic models."""

    name = "ci"
    help = "Train Context-Independent acoustic models"
    description = "Train CI (monophone) models using Baum-Welch algorithm"
    default_model_type = "ci"

    def add_arguments(self, parser: argparse.ArgumentParser) -> None:
        """Add command-specific arguments."""
        super().add_model_arguments(parser)
        parser.add_argument(
            "--flat-dir",
            type=str,
            help="Flat model directory (default: auto from experiment)",
        )
        parser.add_argument(
            "--from",
            type=str,
            dest="from_config",
            help="Start from another config (e.g., --from 1g)",
        )
        parser.add_argument(
            "--features-dir",
            type=str,
            help="Feature directory (default: auto from config)",
        )
        parser.add_argument(
            "--dictionary",
            type=str,
            help="Dictionary file (default: {project_dir}/shared/dictionary.dict)",
        )
        parser.add_argument(
            "--output-dir",
            type=str,
            help="Output model directory (default: auto from experiment)",
        )
        parser.add_argument(
            "--max-iterations",
            type=int,
            default=10,
            help="Maximum training iterations (default: 10)",
        )
        parser.add_argument(
            "--min-iterations",
            type=int,
            default=3,
            help="Minimum iterations before convergence check (default: 3)",
        )
        parser.add_argument(
            "--convergence-threshold",
            type=float,
            default=0.001,
            help="Convergence threshold (default: 0.001)",
        )
        parser.add_argument(
            "--topn",
            type=int,
            help="Top N Gaussians (default: 1 for CI, 4 for CD)",
        )
        parser.add_argument(
            "--save-alignments",
            action="store_true",
            help="Save phone alignments (phseg files)",
        )

    def execute(self, ctx: CommandContext) -> CommandResult:
        """Execute CI training command."""
        model = self.get_model(ctx)
        project_dir = ctx.project_dir

        # Set default topn from model if not provided
        topn = ctx.args.topn if ctx.args.topn else model.default_topn

        # Build training parameters
        training_params = model.get_default_training_params()
        training_params.update(
            {
                "max_iterations": ctx.args.max_iterations,
                "min_iterations": ctx.args.min_iterations,
                "convergence_threshold": ctx.args.convergence_threshold,
                "topn": topn,
                "save_alignments": ctx.args.save_alignments,
            }
        )

        # Get training stages
        stages = model.get_training_stages(project_dir, training_params=training_params)

        ctx.log_action("Train", f"{model.display_name} model")
        ctx.log(f"  Config: {model.config}")
        ctx.log(f"  Experiment: {ctx.experiment}")
        ctx.log(f"  Top N: {topn}")
        ctx.log(f"  Max iterations: {ctx.args.max_iterations}")
        ctx.log(f"  Dependencies: {', '.join(model.get_training_dependencies())}")
        ctx.log(f"  Training stages ({len(stages)}):")
        for i, stage in enumerate(stages, 1):
            deps = f" <- {', '.join(stage.depends_on)}" if stage.depends_on else ""
            ctx.log(f"    {i}. {stage.name}{deps}")

        if ctx.dry_run:
            ctx.emit_blank()
            ctx.log_comment("CI training would run bw iterations here")
            return CommandResult.ok("Dry run complete")

        # TODO: Implement actual CI training via the pipeline runner
        ctx.log("")
        ctx.log("CI training not yet implemented.")
        ctx.log("To train manually, use the flat and bw commands.")

        return CommandResult.fail("Not yet implemented", exit_code=1)


# Singleton instance for registration
ci_command = CICommand()
