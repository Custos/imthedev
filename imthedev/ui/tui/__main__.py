"""Entry point for running the TUI application directly.

This module allows running the TUI with: python -m imthedev.ui.tui
"""

from imthedev.ui.tui.app import ImTheDevApp


def main() -> None:
    """Run the ImTheDevApp TUI application."""
    app = ImTheDevApp()
    app.run()


if __name__ == "__main__":
    main()