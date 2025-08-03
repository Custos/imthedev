# imthedev - AI Workflow Terminal

Terminal app for managing AI development workflows. Keyboard-driven, with command transparency and project-specific context.

## Tech Stack
- Python 3.11+, Textual 5.0.1 (TUI), SQLite, Google Gemini API
- Async-first with asyncio, type-safe with mypy strict

## Working With This Code
1. Never import from UI in core layer
2. All cross-layer communication via events
3. Keep TUI components focused and testable
4. Run component tests separately (known issue)
5. Always avoid creating duplicate code, v2, anything like that.


## Architecture
The app is in ./imthedev/ with architecture below.
```
src/
├── core/        # Business logic - ZERO UI imports
├── infrastructure/  # DB, AI adapters, event bus
├── ui/          # Textual TUI - talks to core via facade/events only
└── tests/       # Comprehensive test coverage
```

**Key Rule**: UI and Core are completely decoupled. Communication only through:
1. `CoreFacade` (UI → Core)
2. Event bus (Core → UI)

## Commands
```bash
poetry install                    # Setup
poetry run python -m src.main     # Run app
poetry run pytest                 # Test
poetry run mypy src/              # Type check
```

## Code Style

### Always Required
- Full type hints on every function
- Async for all I/O operations
- Business logic in domain models, not services

### Example Pattern
```python
# Event-driven communication
@dataclass(frozen=True)
class CommandProposed(Event):
    command: str
    reasoning: str

# Domain model with behavior
class Project:
    def add_context(self, entry: str) -> None:
        """Business logic lives here."""
        # Implementation

# UI subscribes to events
@on(CommandProposed)
async def handle_command(self, event: CommandProposed) -> None:
    await self.show_approval(event.command)
```

See ./docs/ directory for WORKING_ON.md, KNOWN_ISSUES.md, CURRENT_STATE.md, and NEW_FEATURES.md for detailed status, and keep them up to date.