# Claude Project Constitution - imthedev

This document defines the fundamental principles, conventions, and constraints for the imthedev project to ensure consistent, high-quality development with Claude's assistance.

## Project Overview

**imthedev** is a sophisticated, keyboard-driven terminal application for managing SuperClaude workflows. Its purpose is to provide a central hub for orchestrating AI-driven development tasks across multiple projects.

### Core Mission
To create an intuitive, efficient interface that empowers developers to leverage AI capabilities seamlessly within their development workflow, while maintaining complete control and visibility over AI-generated commands and actions.

### Primary Goals
- **Workflow Orchestration**: Manage multiple SuperClaude projects from a single interface
- **Context Persistence**: Maintain project-specific context and history across sessions
- **Command Transparency**: Display AI reasoning and allow approval/rejection of proposed commands
- **Keyboard Efficiency**: Provide a fully keyboard-navigable interface for power users
- **Extensibility**: Design for future expansion to web UIs, IDE plugins, and API access

## Key Technologies & Frameworks

### Primary Language
**Python 3.11+** - Chosen for its robust async support, extensive ecosystem, and excellent AI library integration.

### Core Frameworks
- **Textual** (>=0.40.0) - Modern TUI framework for building sophisticated terminal applications
- **SQLite** (via aiosqlite) - Lightweight, embedded database for project metadata and state persistence
- **asyncio** - Native Python async/await for responsive, non-blocking operations

### AI Integration
- **Anthropic SDK** - Primary integration for Claude models
- **OpenAI SDK** - Secondary support for GPT models
- **Adapter Pattern** - Extensible design for future AI providers

### Development Tools
- **Type Checking**: mypy with strict mode enabled
- **Code Formatting**: black for consistent style
- **Linting**: ruff for fast, comprehensive code analysis
- **Testing**: pytest with pytest-asyncio for async test support

## Architectural Principles

### 1. Complete Layer Decoupling (Non-Negotiable)
The business logic (Core Layer) must be completely decoupled from the presentation (UI) layer. This separation is absolute and enforced through:

- **Protocol-Based Interfaces**: All communication between layers uses Python Protocol classes
- **No Direct Dependencies**: Core layer has zero imports from UI layer
- **Event-Driven Communication**: Layers communicate exclusively through an event bus
- **Facade Pattern**: UI interacts with core only through a simplified facade interface

### 2. Event-Driven Architecture
The system will be event-driven to ensure components are loosely coupled:

- **Central Event Bus**: All cross-component communication flows through the event bus
- **Publish-Subscribe Model**: Components subscribe to relevant events without direct coupling
- **Immutable Events**: Events are immutable data structures with defined schemas
- **Async Event Handling**: All event handlers are async-first for non-blocking operation

### 3. Domain-Driven Design
Core business logic follows DDD principles:

- **Rich Domain Models**: Business logic lives in domain objects, not services
- **Bounded Contexts**: Clear boundaries between different domains (projects, commands, AI)
- **Repository Pattern**: Abstract data persistence behind repository interfaces
- **Value Objects**: Use immutable value objects for data integrity

### 4. Dependency Inversion
High-level modules don't depend on low-level modules:

- **Interface Segregation**: Small, focused interfaces for each capability
- **Dependency Injection**: All dependencies injected through constructors
- **No Global State**: No singletons or global variables
- **Testability First**: Every component designed for easy unit testing

## Coding Conventions

### Python Style Guide
All Python code must strictly adhere to **PEP 8** with the following specifications:

#### Naming Conventions
- **Classes**: PascalCase (e.g., `ProjectManager`, `CommandEngine`)
- **Functions/Methods**: snake_case (e.g., `create_project`, `get_current_context`)
- **Constants**: UPPER_SNAKE_CASE (e.g., `MAX_RETRIES`, `DEFAULT_TIMEOUT`)
- **Private Members**: Leading underscore (e.g., `_internal_state`, `_process_event`)

#### Type Hints (Mandatory)
All functions and methods must include comprehensive type hints:

```python
from typing import Optional, List, Dict, Protocol
from uuid import UUID
from pathlib import Path

async def create_project(
    name: str,
    path: Path,
    settings: Optional[ProjectSettings] = None
) -> Project:
    """Create a new project with the specified configuration.
    
    Args:
        name: Human-readable project name
        path: Filesystem path to project root
        settings: Optional project-specific settings
        
    Returns:
        Newly created Project instance
        
    Raises:
        ProjectExistsError: If project already exists at path
        InvalidPathError: If path is not accessible
    """
    ...
```

#### Documentation Standards
- **Module Docstrings**: Every module must have a docstring explaining its purpose
- **Class Docstrings**: Describe the class's responsibility and usage
- **Method Docstrings**: Include Args, Returns, and Raises sections
- **Inline Comments**: Use sparingly, only for non-obvious logic

#### Code Organization
- **Import Order**: Standard library, third-party, local (alphabetically within each group)
- **Line Length**: Maximum 88 characters (Black default)
- **Function Length**: Prefer functions under 50 lines
- **Class Length**: Prefer classes under 200 lines

### Async Best Practices
- **Async by Default**: All I/O operations must be async
- **No Blocking Calls**: Never use blocking I/O in async functions
- **Proper Cleanup**: Always use async context managers for resources
- **Error Propagation**: Let exceptions bubble up with proper context

### Testing Conventions
- **Test Naming**: `test_<function_name>_<scenario>_<expected_outcome>`
- **AAA Pattern**: Arrange, Act, Assert structure for all tests
- **Isolation**: Each test must be completely independent
- **Mocking**: Mock external dependencies, not internal components

## Project Constraints

### MVP Scope (Strict)
The initial build is an MVP. The following constraints apply:

1. **Feature Freeze**: Avoid adding any features not explicitly defined in `00_WORKFLOW_PLAN.md`
2. **No Premature Optimization**: Prioritize clean, testable architecture over performance
3. **Essential Features Only**:
   - Project management (create, select, switch)
   - Context persistence per project
   - Command proposal and approval workflow
   - Autopilot mode toggle
   - Multi-model AI support
   - Full keyboard navigation


### Commit Conventions
Follow conventional commits:
- `feat:` New features
- `fix:` Bug fixes
- `docs:` Documentation changes
- `test:` Test additions/changes
- `refactor:` Code refactoring
- `chore:` Build/tool changes
