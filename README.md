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

### Core Services

The core layer implements three essential services that power imthedev's functionality:

#### CommandEngine

The `CommandEngineImpl` manages the complete lifecycle of commands from proposal through execution:

- **Command Proposal**: Creates new commands with AI-generated suggestions and reasoning
- **Approval Workflow**: Supports manual approval/rejection of proposed commands
- **Asynchronous Execution**: Executes approved commands using subprocess with real-time output capture
- **Autopilot Mode**: Bypasses approval for trusted workflows when enabled
- **Event-Driven Updates**: Publishes events for each state transition (proposed, approved, rejected, executing, completed, failed)
- **Cancellation Support**: Allows cancellation of long-running commands

The engine ensures safe command execution with comprehensive error handling and maintains a queue of pending commands awaiting user approval.

#### StateManager

The `StateManagerImpl` provides centralized application state management with persistence:

- **Global State Management**: Maintains current project, autopilot mode, selected AI model, and UI preferences
- **State Persistence**: Automatically saves state to JSON files with atomic write operations
- **Event Notifications**: Publishes state change events through the event bus
- **Subscription System**: Supports state change subscriptions with weak references to prevent memory leaks
- **Type-Safe Updates**: Validates all state updates with comprehensive error checking
- **Concurrent Update Handling**: Safely manages concurrent state modifications

The state manager ensures consistent application behavior across sessions and provides a single source of truth for application configuration.

#### AIOrchestrator

The `AIOrchestratorImpl` orchestrates AI interactions using the Adapter Pattern for multi-model support:

- **Multi-Model Support**: Integrates with multiple AI providers through a unified interface
  - Claude (Anthropic): Supports both Opus and Sonnet models
  - OpenAI: Supports GPT-4 and GPT-3.5 Turbo
  - Extensible design for adding new providers
- **Command Generation**: Creates contextually-aware commands based on project history and objectives
- **Result Analysis**: Analyzes command execution results and suggests next actions
- **Token Estimation**: Provides cost estimation for AI operations
- **Adapter Pattern**: Clean abstraction allows easy addition of new AI providers
- **Mock Support**: Includes mock adapter for testing without API dependencies

Each adapter handles provider-specific communication while maintaining a consistent interface for the application.

### Event-Driven Architecture

All core services communicate through a central event bus, ensuring loose coupling and enabling:

- Real-time UI updates without direct dependencies
- Audit trail of all system operations
- Extension points for future features
- Testability through event verification

See `00_WORKFLOW_PLAN.md` for detailed implementation documentation.

## License

This project is licensed under the Elastic License 2.0 (ELv2). See LICENSE file for details.