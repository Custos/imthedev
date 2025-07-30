# imthedev

A sophisticated, keyboard-driven terminal application for managing SuperClaude workflows.

## Overview

imthedev provides a central hub for orchestrating AI-driven development tasks across multiple projects. It features a clean, decoupled architecture that separates business logic from the presentation layer, enabling future expansion to web UIs, IDE extensions, and API access.

## Features

- **Project Management**: Create, select, and switch between multiple projects
- **Context Persistence**: Maintain project-specific context and history across sessions
- **Command Transparency**: Display AI reasoning and allow approval/rejection of proposed commands
- **Keyboard Efficiency**: Fully keyboard-navigable interface for power users
- **Multi-Model Support**: Work with Claude, OpenAI, and future AI models
- **Autopilot Mode**: Continuous auto-approved execution for trusted workflows

## Installation

```bash
# Clone the repository
git clone https://github.com/Custos/imthedev.git
cd imthedev

# Create a virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install in development mode
pip install -e ".[dev]"
```

## Configuration

Set up your AI provider API keys:

```bash
export CLAUDE_API_KEY="your-claude-api-key"
export OPENAI_API_KEY="your-openai-api-key"
```

## Usage

```bash
# Start the TUI application
imthedev

# Initialize configuration (first run)
imthedev init
```

## Development

```bash
# Install development dependencies
pip install -e ".[dev]"

# Run tests
pytest

# Type checking
mypy imthedev

# Code formatting
black imthedev tests
ruff check imthedev tests --fix

# Run tests with coverage
pytest --cov=imthedev --cov-report=html
```

## Architecture

The project follows a clean, layered architecture:

- **Core Layer**: Domain models, service interfaces, and event system
- **Infrastructure Layer**: File system, database, and AI provider integrations
- **Presentation Layer**: Terminal UI (with future support for web and IDE)

See `00_WORKFLOW_PLAN.md` for detailed implementation documentation.

## License

This project is licensed under the Elastic License 2.0 (ELv2). See LICENSE file for details.