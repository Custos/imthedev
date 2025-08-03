"""Tests for the GeminiAdapter implementation.

This module provides comprehensive test coverage for the Google Gemini AI adapter,
including API integration, error handling, and response parsing.
"""

import asyncio
import os
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pytest

from imthedev.core.domain import Command, CommandResult, CommandStatus, ProjectContext
from imthedev.core.services.ai_orchestrator import AIProviderError
from imthedev.core.services.gemini_adapter import GeminiAdapter


@pytest.fixture
def sample_context():
    """Create a sample project context for testing."""
    context = ProjectContext()
    context.ai_memory = "Previous conversation context"
    context.current_state = {"current_dir": "/project", "last_command": "git status"}
    
    # Add some command history
    cmd1 = Command(
        id="cmd1",
        project_id="proj1",
        command_text="git status",
        ai_reasoning="Check repository status",
        status=CommandStatus.COMPLETED,
    )
    cmd1.result = CommandResult(exit_code=0, stdout="Clean", stderr="", execution_time=1.0)
    context.history.append(cmd1)
    
    return context


@pytest.fixture
def gemini_adapter():
    """Create a GeminiAdapter instance with mocked client."""
    with patch.dict(os.environ, {"GEMINI_API_KEY": "test-key"}):
        with patch("imthedev.core.services.gemini_adapter.genai") as mock_genai:
            # Mock the client
            mock_client = MagicMock()
            mock_genai.Client.return_value = mock_client
            
            adapter = GeminiAdapter(api_key="test-key")
            adapter._client = mock_client
            return adapter


class TestGeminiAdapter:
    """Test suite for GeminiAdapter functionality."""
    
    def test_initialization_with_api_key(self):
        """Test adapter initialization with API key."""
        with patch.dict(os.environ, {"GEMINI_API_KEY": "test-key"}):
            with patch("imthedev.core.services.gemini_adapter.genai") as mock_genai:
                mock_client = MagicMock()
                mock_genai.Client.return_value = mock_client
                
                adapter = GeminiAdapter()
                assert adapter._api_key == "test-key"
                assert adapter._model_name == "gemini-2.5-flash"
                assert adapter._client is not None
    
    def test_initialization_without_api_key(self):
        """Test adapter initialization without API key."""
        with patch.dict(os.environ, {}, clear=True):
            adapter = GeminiAdapter()
            assert adapter._api_key == ""
            assert adapter._client is None
            assert not adapter.is_available()
    
    def test_invalid_model_name(self):
        """Test initialization with invalid model name."""
        with pytest.raises(ValueError, match="Unsupported model"):
            GeminiAdapter(model_name="invalid-model")
    
    def test_supported_models(self):
        """Test that all supported models can be initialized."""
        models = ["gemini-2.5-flash", "gemini-2.5-pro", "gemini-2.5-flash-8b"]
        
        for model in models:
            adapter = GeminiAdapter(api_key="test-key", model_name=model)
            assert adapter._model_name == model
            assert model in GeminiAdapter.SUPPORTED_MODELS
    
    def test_is_available(self, gemini_adapter):
        """Test availability check."""
        assert gemini_adapter.is_available()
        
        # Test when client is None
        gemini_adapter._client = None
        assert not gemini_adapter.is_available()
        
        # Test when api_key is empty
        gemini_adapter._api_key = ""
        gemini_adapter._client = MagicMock()
        assert not gemini_adapter.is_available()
    
    @pytest.mark.asyncio
    async def test_generate_command_success(self, gemini_adapter, sample_context):
        """Test successful command generation."""
        # Mock the response
        mock_response = MagicMock()
        mock_response.text = """
        COMMAND: git add -A
        REASONING: Stage all changes for commit based on the clean status
        """
        
        # Mock the generate_content method
        gemini_adapter._client.models.generate_content.return_value = mock_response
        
        # Generate command
        command, reasoning = await gemini_adapter.generate_command(
            sample_context, "Stage all changes"
        )
        
        assert command == "git add -A"
        assert "Stage all changes" in reasoning
        
        # Verify the client was called
        gemini_adapter._client.models.generate_content.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_generate_command_parsing_fallback(self, gemini_adapter, sample_context):
        """Test command generation with parsing fallback."""
        # Mock response without proper format
        mock_response = MagicMock()
        mock_response.text = """
        You should run git commit -m "Initial commit"
        This will create your first commit.
        """
        
        gemini_adapter._client.models.generate_content.return_value = mock_response
        
        command, reasoning = await gemini_adapter.generate_command(
            sample_context, "Create initial commit"
        )
        
        # Should extract the git command
        assert "git commit" in command
        assert reasoning != ""
    
    @pytest.mark.asyncio
    async def test_generate_command_unavailable(self, sample_context):
        """Test command generation when adapter is unavailable."""
        adapter = GeminiAdapter()  # No API key
        
        with pytest.raises(AIProviderError, match="not available"):
            await adapter.generate_command(sample_context, "Test objective")
    
    @pytest.mark.asyncio
    async def test_generate_command_api_error(self, gemini_adapter, sample_context):
        """Test command generation with API error."""
        gemini_adapter._client.models.generate_content.side_effect = Exception("API Error")
        
        with pytest.raises(AIProviderError, match="command generation failed"):
            await gemini_adapter.generate_command(sample_context, "Test objective")
    
    @pytest.mark.asyncio
    async def test_analyze_result_success(self, gemini_adapter, sample_context):
        """Test successful result analysis."""
        command = Command(
            id="test-cmd",
            project_id="test-proj",
            command_text="npm test",
            ai_reasoning="Run tests",
            status=CommandStatus.COMPLETED,
        )
        command.result = CommandResult(
            exit_code=0,
            stdout="All tests passed",
            stderr="",
            execution_time=5.0
        )
        
        # Mock the response
        mock_response = MagicMock()
        mock_response.text = """
        SUCCESS: true
        SUMMARY: All tests passed successfully
        NEXT_STEPS: Deploy the application
        """
        
        gemini_adapter._client.models.generate_content.return_value = mock_response
        
        analysis = await gemini_adapter.analyze_result(
            command, "All tests passed", sample_context
        )
        
        assert analysis.success is True
        assert "All tests passed" in analysis.summary
        assert "Deploy" in analysis.suggestions[0]
    
    @pytest.mark.asyncio
    async def test_analyze_result_failure(self, gemini_adapter, sample_context):
        """Test result analysis for failed command."""
        command = Command(
            id="test-cmd",
            project_id="test-proj",
            command_text="npm test",
            ai_reasoning="Run tests",
            status=CommandStatus.FAILED,
        )
        command.result = CommandResult(
            exit_code=1,
            stdout="",
            stderr="Test failures",
            execution_time=3.0
        )
        
        mock_response = MagicMock()
        mock_response.text = """
        SUCCESS: false
        SUMMARY: Tests failed with errors
        NEXT_STEPS: 
        - Review test failures
        - Fix the failing tests
        """
        
        gemini_adapter._client.models.generate_content.return_value = mock_response
        
        analysis = await gemini_adapter.analyze_result(
            command, "Test failures", sample_context
        )
        
        assert analysis.success is False
        assert analysis.confidence < 0.5
        assert len(analysis.suggestions) > 0
    
    @pytest.mark.asyncio
    async def test_estimate_tokens(self, gemini_adapter, sample_context):
        """Test token estimation."""
        tokens = await gemini_adapter.estimate_tokens(
            sample_context, "Create a new feature"
        )
        
        # Should return a reasonable estimate
        assert tokens > 0
        assert tokens < 10000  # Reasonable upper bound
    
    def test_build_context_prompt(self, gemini_adapter, sample_context):
        """Test context prompt building."""
        prompt = gemini_adapter._build_context_prompt(sample_context)
        
        assert "Recent Command History" in prompt
        assert "git status" in prompt
        assert "Current Project State" in prompt
        assert "/project" in prompt
        assert "Previous Context" in prompt
    
    def test_create_command_generation_prompt(self, gemini_adapter):
        """Test command generation prompt creation."""
        context = "Test context"
        objective = "Deploy application"
        
        prompt = gemini_adapter._create_command_generation_prompt(context, objective)
        
        assert "Test context" in prompt
        assert "Deploy application" in prompt
        assert "COMMAND:" in prompt
        assert "REASONING:" in prompt
    
    def test_parse_command_response(self, gemini_adapter):
        """Test command response parsing."""
        # Test proper format
        response = """
        COMMAND: docker build -t app .
        REASONING: Build Docker image for deployment
        """
        
        command, reasoning = gemini_adapter._parse_command_response(response)
        assert command == "docker build -t app ."
        assert "Build Docker image" in reasoning
        
        # Test without proper format
        response = "Run npm install to install dependencies"
        command, reasoning = gemini_adapter._parse_command_response(response)
        assert "npm" in command
        assert reasoning != ""
    
    def test_parse_analysis_response(self, gemini_adapter):
        """Test analysis response parsing."""
        # Test proper format
        response = """
        SUCCESS: true
        SUMMARY: Operation completed successfully
        NEXT_STEPS:
        - Continue with deployment
        - Monitor application
        """
        
        analysis = gemini_adapter._parse_analysis_response(response)
        assert analysis.success is True
        assert "completed successfully" in analysis.summary
        assert len(analysis.suggestions) >= 2
        
        # Test fallback parsing
        response = "The command seemed to work fine"
        analysis = gemini_adapter._parse_analysis_response(response)
        assert analysis.summary != ""
        assert len(analysis.suggestions) > 0
    
    def test_get_model_info(self, gemini_adapter):
        """Test getting model information."""
        info = gemini_adapter.get_model_info()
        
        assert info["provider"] == "Google Gemini"
        assert info["model"] == "gemini-2.5-flash"
        assert "description" in info
        assert "max_tokens" in info
        assert info["available"] is True
    
    @pytest.mark.asyncio
    async def test_async_generation(self, gemini_adapter):
        """Test that async generation works properly."""
        mock_response = MagicMock()
        mock_response.text = "COMMAND: ls\nREASONING: List files"
        
        gemini_adapter._client.models.generate_content.return_value = mock_response
        
        # Test that it runs asynchronously
        result = await gemini_adapter._generate_async("test prompt")
        assert result == "COMMAND: ls\nREASONING: List files"
        
        # Verify the client was called with correct parameters
        gemini_adapter._client.models.generate_content.assert_called_once()
        call_args = gemini_adapter._client.models.generate_content.call_args
        assert call_args[1]["model"] == "gemini-2.5-flash"
        assert call_args[1]["contents"] == "test prompt"


class TestGeminiIntegration:
    """Integration tests for GeminiAdapter with orchestrator."""
    
    @pytest.mark.asyncio
    async def test_orchestrator_integration(self):
        """Test that GeminiAdapter integrates with AIOrchestrator."""
        from imthedev.core.events import EventBus
        from imthedev.core.interfaces import AIModel
        from imthedev.core.services.ai_orchestrator import AIOrchestratorImpl
        
        with patch.dict(os.environ, {"GEMINI_API_KEY": "test-key"}):
            with patch("imthedev.core.services.gemini_adapter.genai"):
                event_bus = EventBus("test")
                orchestrator = AIOrchestratorImpl(event_bus)
                
                # Check that Gemini models are available
                models = orchestrator.get_available_models()
                assert AIModel.GEMINI_FLASH in models
                assert AIModel.GEMINI_PRO in models
                assert AIModel.GEMINI_FLASH_8B in models
    
    @pytest.mark.asyncio
    async def test_model_selection(self):
        """Test that correct Gemini model can be selected."""
        from imthedev.core.events import EventBus
        from imthedev.core.interfaces import AIModel
        from imthedev.core.services.ai_orchestrator import AIOrchestratorImpl
        
        with patch.dict(os.environ, {"GEMINI_API_KEY": "test-key"}):
            with patch("imthedev.core.services.gemini_adapter.genai"):
                event_bus = EventBus("test")
                orchestrator = AIOrchestratorImpl(event_bus)
                
                # Get the Gemini Flash adapter
                adapter = orchestrator._adapters.get(AIModel.GEMINI_FLASH)
                assert adapter is not None
                assert adapter._model_name == "gemini-2.5-flash"
                
                # Get the Gemini Pro adapter
                adapter = orchestrator._adapters.get(AIModel.GEMINI_PRO)
                assert adapter is not None
                assert adapter._model_name == "gemini-2.5-pro"