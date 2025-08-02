"""Main entry point for the imthedev package.

This module provides the main entry point for running the imthedev application.
It handles application bootstrap, execution, and cleanup.
"""

import asyncio
import sys

from imthedev.app.bootstrap import bootstrap_application


async def main(config_file: str | None = None) -> None:
    """Main entry point for the imthedev application.

    This function bootstraps the application and runs it until completion
    or interruption. It handles proper cleanup in all cases.

    Args:
        config_file: Optional path to configuration file
    """
    app = None
    try:
        # Bootstrap the application with all dependencies
        app = await bootstrap_application(config_file)

        # Run the application
        await app.run()

    except KeyboardInterrupt:
        print("\nApplication interrupted by user")
    except Exception as e:
        print(f"Application failed: {e}", file=sys.stderr)
        sys.exit(1)
    finally:
        if app:
            await app.cleanup()


def cli_main() -> None:
    """Synchronous entry point for CLI script."""
    config_file = sys.argv[1] if len(sys.argv) > 1 else None
    asyncio.run(main(config_file))


if __name__ == "__main__":
    # Allow running directly with optional config file argument
    config_file = sys.argv[1] if len(sys.argv) > 1 else None
    asyncio.run(main(config_file))
