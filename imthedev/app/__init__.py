"""Application bootstrap and main entry point for imthedev.

This package contains the application bootstrap functionality including:
- Dependency injection and service initialization
- Application lifecycle management
- Configuration and setup
"""

from imthedev.app.bootstrap import ImTheDevApp, bootstrap_application

__all__ = ["ImTheDevApp", "bootstrap_application"]