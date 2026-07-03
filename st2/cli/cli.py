"""Command-line interface for ST2.

Thin wrapper around st2.api - all business logic lives in the library.
"""

import argparse
import sys

from st2 import __version__
from st2.cli.base import add_dry_run_argument, add_json_argument


def main() -> int:
    parser = argparse.ArgumentParser(
        prog="st2",
        description="ST2 - Acoustic model training toolkit",
    )
    parser.add_argument(
        "-V",
        "--version",
        action="version",
        version=f"st2 {__version__}",
    )
    add_json_argument(parser)
    add_dry_run_argument(parser)

    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # Import command instances
    from st2.cli.align import align_command
    from st2.cli.build import build_command
    from st2.cli.clean import clean_command
    from st2.cli.compare import compare_command
    from st2.cli.config import register_config_command
    from st2.cli.features import features_command
    from st2.cli.flat import flat_command
    from st2.cli.info import info_command
    from st2.cli.setup import setup_command
    from st2.cli.split import split_command
    from st2.cli.step import register_step_command
    from st2.cli.test import test_command
    from st2.cli.validate import validate_command

    # Register Command-based commands
    commands = [
        setup_command,
        build_command,
        split_command,
        features_command,
        flat_command,
        clean_command,
        validate_command,
        test_command,
        align_command,
        info_command,
        compare_command,
    ]
    for cmd in commands:
        cmd.register(subparsers)

    # Register commands with subcommands
    register_config_command(subparsers)
    register_step_command(subparsers)

    args = parser.parse_args()

    if args.command is None:
        parser.print_help()
        return 0

    # Execute command
    from st2.cli.base import execute_command

    return execute_command(args)


if __name__ == "__main__":
    sys.exit(main())
