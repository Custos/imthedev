# Google Gemini 2.5 Integration Guide

This guide covers the integration of Google's Gemini 2.5 models (Flash, Pro, and Flash-8B) into the imthedev AI orchestration system.

## Overview

The GeminiAdapter provides seamless integration with Google's Gemini 2.5 family of models, offering:
- **Gemini 2.5 Flash**: Fast and efficient for quick responses
- **Gemini 2.5 Pro**: Advanced capabilities for complex reasoning
- **Gemini 2.5 Flash-8B**: Lightweight model for simple tasks

## Installation

### 1. Install the Google AI SDK

```bash
pip install google-generativeai
```

### 2. Obtain an API Key

Get your Gemini API key from: https://aistudio.google.com/apikey

### 3. Configure Environment

Set your API key as an environment variable:

```bash
export GEMINI_API_KEY="your-api-key-here"
```

Or add it to your `.env` file:

```env
GEMINI_API_KEY=your-api-key-here
```

## Configuration

### Update Configuration File

The Gemini integration can be configured in your `~/.imthedev/config.toml`:

```toml
[ai]
default_model = "gemini-2.5-flash"  # or "claude", "gpt-4", etc.
gemini_api_key = ""  # Leave empty to use environment variable
gemini_model = "gemini-2.5-flash"  # Options: gemini-2.5-flash, gemini-2.5-pro, gemini-2.5-flash-8b
```

### Available Models

| Model | Description | Use Case | Max Tokens |
|-------|-------------|----------|------------|
| `gemini-2.5-flash` | Fast and efficient | Quick commands, simple tasks | 8,192 |
| `gemini-2.5-pro` | Advanced reasoning | Complex analysis, architecture | 32,768 |
| `gemini-2.5-flash-8b` | Lightweight | Basic operations, low resource | 8,192 |

## Usage

### Using Gemini in imthedev

Once configured, Gemini models are automatically available in the AI model selection:

1. **Via Configuration**: Set `default_model = "gemini-2.5-flash"` in config
2. **Via UI**: Select Gemini model in the configuration screen (Ctrl+S)
3. **Programmatically**: Specify model when generating commands

### Code Example

```python
from imthedev.core.services.gemini_adapter import GeminiAdapter
from imthedev.core.domain import ProjectContext

# Initialize adapter
adapter = GeminiAdapter(
    api_key="your-api-key",  # Optional, uses env var if not provided
    model_name="gemini-2.5-flash"
)

# Check availability
if adapter.is_available():
    # Generate a command
    context = ProjectContext()
    command, reasoning = await adapter.generate_command(
        context, 
        "Create a Python virtual environment"
    )
    print(f"Command: {command}")
    print(f"Reasoning: {reasoning}")
```

## Architecture

### Adapter Pattern Implementation

The GeminiAdapter follows the established AIAdapter interface:

```python
class GeminiAdapter(AIAdapter):
    """Adapter for Google's Gemini 2.5 models."""
    
    async def generate_command(self, context, objective) -> tuple[str, str]:
        """Generate shell commands using Gemini."""
        
    async def analyze_result(self, command, output, context) -> CommandAnalysis:
        """Analyze command results for success/failure."""
        
    async def estimate_tokens(self, context, objective) -> int:
        """Estimate token usage for cost management."""
        
    def is_available(self) -> bool:
        """Check if adapter is properly configured."""
```

### Integration Points

1. **AI Orchestrator**: Automatically registers Gemini models when API key is present
2. **Configuration Manager**: Supports Gemini-specific settings
3. **UI Components**: Configuration screen includes Gemini API key field
4. **Command Engine**: Seamlessly uses Gemini for command generation

## Features

### Command Generation

The adapter generates shell commands based on:
- Project context and history
- Current state information
- User objectives
- Previous command results

Example prompt structure:
```
CONTEXT: [Recent commands, current state, AI memory]
OBJECTIVE: [User's goal]
→ COMMAND: [Generated shell command]
→ REASONING: [Explanation of approach]
```

### Result Analysis

Analyzes command execution results to:
- Determine success/failure
- Suggest next steps
- Update project state
- Learn from outcomes

### Token Management

- Estimates token usage before API calls
- Tracks costs across different models
- Optimizes prompts for efficiency

## Testing

### Running Tests

```bash
# Run Gemini adapter tests
pytest tests/core/services/test_gemini_adapter.py -v

# Run with coverage
pytest tests/core/services/test_gemini_adapter.py --cov=imthedev.core.services.gemini_adapter
```

### Test Coverage

The test suite covers:
- Adapter initialization with various configurations
- Command generation and parsing
- Result analysis and interpretation
- Error handling and fallbacks
- Integration with AI orchestrator
- Token estimation accuracy

## Troubleshooting

### Common Issues

1. **Import Error**: "Google AI SDK not installed"
   ```bash
   pip install google-generativeai
   ```

2. **API Key Not Found**: "Gemini adapter is not available"
   - Ensure `GEMINI_API_KEY` environment variable is set
   - Check configuration file for typos

3. **Model Not Supported**: "Unsupported model: [model-name]"
   - Use one of: `gemini-2.5-flash`, `gemini-2.5-pro`, `gemini-2.5-flash-8b`

4. **Rate Limiting**: API request failures
   - Implement exponential backoff
   - Consider using different model for high-volume operations

### Debug Logging

Enable debug logging to troubleshoot issues:

```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

## Performance Considerations

### Model Selection Guidelines

- **High Volume**: Use `gemini-2.5-flash` for speed
- **Complex Tasks**: Use `gemini-2.5-pro` for accuracy
- **Resource Constrained**: Use `gemini-2.5-flash-8b` for efficiency

### Optimization Tips

1. **Context Management**: Keep context concise but informative
2. **Prompt Engineering**: Use clear, structured prompts
3. **Caching**: Reuse similar command patterns
4. **Batch Operations**: Group related requests when possible

## Security

### API Key Management

- **Never commit API keys** to version control
- Use environment variables or secure key management
- Rotate keys regularly
- Monitor usage for anomalies

### Command Validation

The adapter includes safety measures:
- Validates generated commands before execution
- Flags potentially dangerous operations
- Requires user approval for sensitive commands

## Future Enhancements

Planned improvements for Gemini integration:

1. **Streaming Responses**: Real-time command generation
2. **Fine-tuning Support**: Custom model training
3. **Multi-modal Input**: Image and code analysis
4. **Caching Layer**: Reduce API calls for common patterns
5. **Cost Tracking**: Detailed usage analytics

## Contributing

To contribute to the Gemini integration:

1. Fork the repository
2. Create a feature branch
3. Add tests for new functionality
4. Update documentation
5. Submit a pull request

## Support

For issues or questions:
- Open an issue on GitHub
- Check existing documentation
- Review test cases for examples
- Contact maintainers

## License

The Gemini integration follows the main project's Elastic License 2.0 (ELv2).