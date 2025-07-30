"""Global test configuration and fixtures for the imthedev test suite.

This module provides common fixtures and configuration that can be shared
across all test modules.
"""

import sys
from unittest.mock import MagicMock

# Mock textual and other optional dependencies to avoid import errors during testing
textual_mock = MagicMock()
sys.modules['textual'] = textual_mock  
sys.modules['textual.app'] = MagicMock()
sys.modules['textual.widget'] = MagicMock()
sys.modules['textual.widgets'] = MagicMock()
sys.modules['textual.containers'] = MagicMock()
sys.modules['textual.events'] = MagicMock()
sys.modules['textual.screen'] = MagicMock()
sys.modules['textual.reactive'] = MagicMock()
sys.modules['textual.message'] = MagicMock()
sys.modules['textual.geometry'] = MagicMock()
sys.modules['textual.strip'] = MagicMock()

# Mock anthropic and openai to avoid requiring API keys during testing
sys.modules['anthropic'] = MagicMock()
sys.modules['openai'] = MagicMock()