"""Integration tests for Pinecone Assistant MCP."""

import pytest
import asyncio
import json
import tempfile
import os
from unittest.mock import Mock, patch, AsyncMock
from pathlib import Path

from src.config.config import Settings
from src.models.models import (
    Message, AssistantChatParams, StrategySearchParams,
    AssistantContextParams, StrategyContextParams
)
from src.api.assistant_client import AssistantClientManager, PineconeAssistantClient
from src.services.strategic_search import StrategySearchProcessor
from src.services.strategic_context import StrategicContextSearcher
from src.server import initialize, call_tool


class TestIntegrationSetup:
    """Test integration setup and initialization."""

    @pytest.fixture
    def mock_settings(self):
        """Create mock settings for testing."""
        return Settings(
            pinecone_assistant_api_key="pcsk_test_key_12345678901234567890",
            pinecone_assistant_host="https://test.pinecone.io",
            pinecone_assistant_name="test-assistant",
            pinecone_assistant_model="gpt-4o"
        )

    @pytest.fixture
    def temp_yaml_file(self):
        """Create temporary YAML file for testing."""
        yaml_content = """
test_domain:
  searches:
    - name: "basic_search"
      query: "Basic search for {primary}"
      description: "Basic search pattern"
      enabled: true
    - name: "advanced_search" 
      query: "Advanced {primary} with {key_terms}"
      description: "Advanced search pattern"
      enabled: true
    - name: "disabled_search"
      query: "Disabled {primary}"
      description: "Disabled search"
      enabled: false

legal_domain:
  searches:
    - name: "legal_analysis"
      query: "Legal analysis of {primary} under {key_terms}"
      description: "Legal analysis pattern"
      enabled: true
        """
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            f.write(yaml_content)
            temp_path = f.name
            
        yield temp_path
        
        # Cleanup
        os.unlink(temp_path)

    @patch.dict(os.environ, {
        'PINECONE_ASSISTANT_API_KEY': 'pcsk_test_key_12345678901234567890',
        'PINECONE_ASSISTANT_HOST': 'https://test.pinecone.io',
        'PINECONE_ASSISTANT_NAME': 'test-assistant'
    })
    @patch('src.config.config.get_secure_api_key')
    def test_environment_configuration(self, mock_secure_key):
        """Test configuration loading from environment."""
        mock_secure_key.return_value = None  # Force env var usage
        
        settings = Settings()
        
        assert settings.pinecone_assistant_api_key.startswith('pcsk_')
        assert settings.pinecone_assistant_host == 'https://test.pinecone.io'
        assert settings.pinecone_assistant_name == 'test-assistant'

    def test_strategic_search_yaml_loading(self, temp_yaml_file):
        """Test strategic search YAML loading."""
        processor = StrategySearchProcessor(yaml_path=temp_yaml_file)
        
        domains = processor.get_available_domains()
        assert "test_domain" in domains
        assert "legal_domain" in domains
        
        # Test enabled searches only
        test_searches = processor.get_domain_searches("test_domain")
        assert len(test_searches) == 2  # Only enabled searches
        
        search_names = [s.name for s in test_searches]
        assert "basic_search" in search_names
        assert "advanced_search" in search_names
        assert "disabled_search" not in search_names

    @patch('src.api.assistant_client.Pinecone')
    def test_client_manager_initialization(self, mock_pinecone, mock_settings):
        """Test AssistantClientManager initialization."""
        # Mock successful connection test
        mock_assistant = Mock()
        mock_assistant.chat.return_value = {
            "message": {"role": "assistant", "content": "Test response"},
            "finish_reason": "stop",
            "citations": [],
            "usage": {"input_tokens": 10, "output_tokens": 5}
        }

        mock_pc = Mock()
        mock_pc.assistant.Assistant.return_value = mock_assistant
        mock_pinecone.return_value = mock_pc

        client = AssistantClientManager.get_client(mock_settings)

        assert client is not None
        assert isinstance(client, PineconeAssistantClient)

        # Test connection
        assert client.test_connection() is True
        
        # Verify cleanup
        AssistantClientManager.close()


class TestToolIntegration:
    """Test MCP tool integration."""

    @pytest.fixture
    def mock_client_manager(self):
        """Mock client manager for tool testing."""
        with patch('src.server._client') as mock_client:
            # Mock basic responses
            mock_client.chat.return_value = {
                "message": {"role": "assistant", "content": "Test response"},
                "finish_reason": "stop",
                "citations": [],
                "usage": {"input_tokens": 100, "output_tokens": 50}
            }
            
            mock_client.context.return_value = {
                "chunks": [
                    {
                        "text": "Test document chunk",
                        "score": 0.95,
                        "metadata": {"source": "test.md", "page": 1}
                    }
                ],
                "usage": {"context_tokens": 200}
            }
            
            yield mock_client

    @pytest.fixture
    def mock_search_processor(self):
        """Mock search processor for tool testing."""
        with patch('src.server._search_processor') as mock_processor:
            mock_processor.get_available_domains.return_value = ["test_domain"]
            mock_processor.validate_domain.return_value = True
            mock_processor.execute_strategic_search.return_value = {
                "results": [
                    {
                        "search_name": "test_search",
                        "response": "Test strategic response",
                        "citations": []
                    }
                ],
                "total_usage": {"input_tokens": 300, "output_tokens": 100}
            }
            
            yield mock_processor

    @pytest.fixture
    def mock_context_searcher(self):
        """Mock context searcher for tool testing."""
        with patch('src.server._context_searcher') as mock_searcher:
            mock_searcher.execute_strategic_context_search.return_value = {
                "results": [
                    {
                        "search_name": "test_search",
                        "chunks": [
                            {
                                "text": "Strategic context chunk",
                                "score": 0.90,
                                "metadata": {"source": "test.md"}
                            }
                        ]
                    }
                ],
                "total_usage": {"context_tokens": 150}
            }
            
            yield mock_searcher

    @pytest.mark.asyncio
    async def test_assistant_chat_tool(self, mock_client_manager):
        """Test assistant_chat tool integration."""
        args = {
            "messages": [
                {"role": "user", "content": "Test question"}
            ],
            "model": "gpt-4o",
            "include_highlights": True
        }
        
        response = await call_tool("assistant_chat", args)

        assert len(response) == 1
        # Response is now clean text (not JSON): answer content + optional sources + token summary
        text = response[0].text
        assert "Test response" in text

    @pytest.mark.asyncio
    async def test_assistant_context_tool(self, mock_client_manager):
        """Test assistant_context tool integration."""
        args = {
            "query": "test query",
            "top_k": 3,
            "snippet_size": 1024
        }
        
        response = await call_tool("assistant_context", args)
        
        assert len(response) == 1
        response_data = json.loads(response[0].text)
        
        assert "chunks" in response_data
        assert len(response_data["chunks"]) >= 1
        assert response_data["chunks"][0]["text"] == "Test document chunk"

    @pytest.mark.asyncio
    async def test_strategic_multi_search_tool(self, mock_client_manager, mock_search_processor):
        """Test assistant_strategic_multi_search_chat tool integration."""
        args = {
            "query": "test strategic query",
            "domain": "test_domain",
            "max_searches": 2,
            "model": "gpt-4o"
        }
        
        response = await call_tool("assistant_strategic_multi_search_chat", args)
        
        assert len(response) == 1
        response_data = json.loads(response[0].text)
        
        assert "results" in response_data
        assert "total_usage" in response_data
        
        # Verify search processor was called
        mock_search_processor.execute_strategic_search.assert_called_once()

    @pytest.mark.asyncio
    async def test_strategic_context_search_tool(self, mock_client_manager, mock_search_processor, mock_context_searcher):
        """Test assistant_strategic_multi_search_context tool integration."""
        args = {
            "query": "test context query",
            "domain": "test_domain",
            "top_k": 5,
            "snippet_size": 2048
        }

        response = await call_tool("assistant_strategic_multi_search_context", args)

        assert len(response) == 1
        response_data = json.loads(response[0].text)

        assert "results" in response_data
        assert "total_usage" in response_data

        # Verify context searcher was called
        mock_context_searcher.execute_strategic_context_search.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_configuration_tool(self):
        """Test update_configuration tool integration."""
        with patch('src.server.AssistantClientManager') as mock_manager:
            mock_manager.update_configuration.return_value = {
                "status": "success",
                "changes": {
                    "assistant_name": {
                        "old": "old-assistant",
                        "new": "new-assistant"
                    }
                },
                "current_config": {
                    "assistant_name": "new-assistant",
                    "assistant_host": "https://test.pinecone.io",
                    "model": "gpt-4o"
                }
            }
            
            args = {
                "assistant_name": "new-assistant",
                "model": "claude-3-5-sonnet"
            }
            
            response = await call_tool("update_configuration", args)
            
            assert len(response) == 1
            response_text = response[0].text
            
            assert "✅ Configuration updated successfully!" in response_text
            assert "new-assistant" in response_text

    @pytest.mark.asyncio
    async def test_evaluate_answer_tool(self, mock_client_manager):
        """Test evaluate_answer tool integration (success path, fully mocked)."""
        mock_client_manager.evaluate.return_value = {
            "metrics": {
                "alignment": 0.85,
                "correctness": 0.90,
                "completeness": 0.80
            },
            "reasoning": {
                "evaluated_facts": [
                    {
                        "fact": {"content": "Alice test has two steps"},
                        "entailment": {"value": "entailed"}
                    },
                    {
                        "fact": {"content": "Step 2A asks whether claims are directed to abstract idea"},
                        "entailment": {"value": "entailed"}
                    },
                    {
                        "fact": {"content": "Alice overruled Bilski"},
                        "entailment": {"value": "contradicted"}
                    }
                ]
            },
            "usage": {
                "prompt_tokens": 500,
                "completion_tokens": 120,
                "total_tokens": 620
            }
        }

        args = {
            "question": "What is the Alice two-step test?",
            "answer": "The Alice test has two steps...",
            "ground_truth_answer": "Alice Corp v. CLS Bank established a two-part test..."
        }

        response = await call_tool("evaluate_answer", args)

        assert len(response) == 1
        text = response[0].text
        assert "Alignment Scores:" in text
        assert "0.850" in text   # alignment score
        assert "0.900" in text   # correctness score
        assert "0.800" in text   # completeness score
        assert "Evaluated Facts:" in text
        assert "✅" in text       # entailed fact
        assert "❌" in text       # contradicted fact
        assert "620" in text     # total tokens

    @pytest.mark.asyncio
    async def test_evaluate_answer_free_tier_error(self, mock_client_manager):
        """Test evaluate_answer returns VALIDATION_ERROR on free-tier restriction."""
        mock_client_manager.evaluate.side_effect = ValueError(
            "evaluate_answer requires a Pinecone Standard (paid) plan. "
            "The evaluation endpoint is not available on the free tier."
        )

        args = {
            "question": "What is Section 101?",
            "answer": "Section 101 defines patentable subject matter.",
            "ground_truth_answer": "Section 101 of Title 35 defines what may be patented."
        }

        response = await call_tool("evaluate_answer", args)

        assert len(response) == 1
        error_data = json.loads(response[0].text)
        assert error_data["error"] is True
        assert error_data["code"] == "VALIDATION_ERROR"
        assert "paid" in error_data["message"].lower() or "paid" in str(error_data).lower()

    @pytest.mark.asyncio
    async def test_assistant_context_multimodal_params(self, mock_client_manager):
        """Test that multimodal and include_binary_content params are forwarded to client."""
        args = {
            "query": "test multimodal query",
            "top_k": 3,
            "multimodal": False,
            "include_binary_content": False
        }

        response = await call_tool("assistant_context", args)

        assert len(response) == 1
        # Verify client.context was called and response is valid
        response_data = json.loads(response[0].text)
        assert "chunks" in response_data

        # Verify the params were forwarded: inspect the call args
        call_args = mock_client_manager.context.call_args
        assert call_args is not None
        passed_params = call_args[0][0]  # positional first arg is AssistantContextParams
        assert passed_params.multimodal is False
        assert passed_params.include_binary_content is False

    @pytest.mark.asyncio
    async def test_invalid_tool_name(self):
        """Test handling of invalid tool names."""
        response = await call_tool("invalid_tool", {})
        
        assert len(response) == 1
        assert "Unknown tool: invalid_tool" in response[0].text

    @pytest.mark.asyncio
    async def test_tool_error_handling(self, mock_client_manager):
        """Test tool error handling."""
        # Make the mock client raise an exception
        mock_client_manager.chat.side_effect = Exception("Test error")
        
        args = {
            "messages": [
                {"role": "user", "content": "Test question"}
            ]
        }
        
        response = await call_tool("assistant_chat", args)

        assert len(response) == 1
        # Check for structured error response
        import json
        error_data = json.loads(response[0].text)
        assert error_data["error"] is True
        assert error_data["code"] == "INTERNAL_ERROR"
        assert "request_id" in error_data


class TestEndToEndWorkflow:
    """Test end-to-end workflow scenarios."""

    @pytest.fixture
    def mock_full_environment(self):
        """Mock full environment for end-to-end testing."""
        # Create mocks manually instead of relying on patch.multiple() return value
        mock_settings = Mock()
        mock_client = Mock()
        mock_search_processor = Mock()
        mock_context_searcher = Mock()

        # Configure mocks for realistic workflow
        mock_client.chat.return_value = {
            "message": {
                "role": "assistant",
                "content": "Based on the documents, here is the analysis..."
            },
            "finish_reason": "stop",
            "citations": [
                {
                    "text": "Relevant citation text",
                    "source": "MPEP Section 101"
                }
            ],
            "usage": {"input_tokens": 1500, "output_tokens": 300}
        }

        mock_client.context.return_value = {
            "chunks": [
                {
                    "text": "Section 101 patent eligibility requires...",
                    "score": 0.92,
                    "metadata": {"source": "MPEP_101.md", "page": 1}
                },
                {
                    "text": "Alice framework analysis involves...",
                    "score": 0.88,
                    "metadata": {"source": "Alice_guidance.md", "page": 3}
                }
            ],
            "usage": {"context_tokens": 800}
        }

        mock_search_processor.get_available_domains.return_value = [
            "core_examination_framework", "software_ai_technology"
        ]
        mock_search_processor.validate_domain.return_value = True
        mock_search_processor.execute_strategic_search.return_value = {
            "results": [
                {
                    "search_name": "eligibility_analysis",
                    "query": "Section 101 eligibility analysis Alice Mayo framework software patents",
                    "response": "Detailed eligibility analysis...",
                    "citations": [{"text": "Citation 1", "source": "MPEP"}]
                },
                {
                    "search_name": "software_patent_guidance",
                    "query": "Software computer-implemented invention examination 101 abstract idea software patents",
                    "response": "Software patent guidance...",
                    "citations": [{"text": "Citation 2", "source": "Guidelines"}]
                }
            ],
            "aggregate_response": "Comprehensive analysis of software patent eligibility...",
            "total_usage": {"input_tokens": 2400, "output_tokens": 600}
        }

        mock_context_searcher.execute_strategic_context_search.return_value = {
            "results": [
                {
                    "search_name": "context_search_1",
                    "snippets": [
                        {
                            "text": "Context snippet 1...",
                            "score": 0.95,
                            "metadata": {"source": "doc1.md"}
                        }
                    ]
                }
            ],
            "total_usage": {"context_tokens": 500}
        }

        with patch.multiple(
            'src.server',
            _settings=mock_settings,
            _client=mock_client,
            _search_processor=mock_search_processor,
            _context_searcher=mock_context_searcher
        ):
            # Return dictionary with all mocks
            mocks = {
                '_settings': mock_settings,
                '_client': mock_client,
                '_search_processor': mock_search_processor,
                '_context_searcher': mock_context_searcher
            }
            yield mocks

    @pytest.mark.asyncio
    async def test_research_workflow_context_first(self, mock_full_environment):
        """Test recommended workflow: context first, then AI if needed."""
        
        # Step 1: Use assistant_context for efficient document retrieval
        context_args = {
            "query": "software patent eligibility Section 101 Alice framework",
            "top_k": 5,
            "snippet_size": 2048
        }
        
        context_response = await call_tool("assistant_context", context_args)
        context_data = json.loads(context_response[0].text)
        
        assert "chunks" in context_data
        assert len(context_data["chunks"]) >= 2
        assert context_data["usage"]["context_tokens"] == 800
        
        # Step 2: If more analysis needed, use strategic search
        strategic_args = {
            "query": "software patent eligibility",
            "domain": "software_ai_technology",
            "max_searches": 2,
            "model": "gpt-4o"
        }
        
        strategic_response = await call_tool("assistant_strategic_multi_search_chat", strategic_args)
        strategic_data = json.loads(strategic_response[0].text)
        
        assert "results" in strategic_data
        assert len(strategic_data["results"]) == 2
        assert "aggregate_response" in strategic_data
        assert strategic_data["total_usage"]["input_tokens"] == 2400

    @pytest.mark.asyncio
    async def test_multi_assistant_workflow(self, mock_full_environment):
        """Test multi-assistant switching workflow."""

        # Step 1: Start with MPEP assistant
        update_args = {
            "assistant_name": "mpep-assistant",
            "model": "gpt-4o"
        }

        with patch('src.server.AssistantClientManager.update_configuration') as mock_update, \
             patch('src.server.AssistantClientManager.get_client') as mock_get_client:
            mock_update.return_value = {
                "status": "success",
                "changes": {"assistant_name": {"old": "old", "new": "mpep-assistant"}},
                "current_config": {
                    "assistant_name": "mpep-assistant",
                    "assistant_host": "https://test.pinecone.io",
                    "model": "gpt-4o"
                }
            }
            mock_get_client.return_value = mock_full_environment['_client']

            update_response = await call_tool("update_configuration", update_args)
            assert "✅ Configuration updated successfully!" in update_response[0].text
        
        # Step 2: Research with MPEP assistant
        mpep_args = {
            "query": "Section 101 eligibility requirements",
            "top_k": 3,
            "snippet_size": 1024
        }
        
        mpep_response = await call_tool("assistant_context", mpep_args)
        mpep_data = json.loads(mpep_response[0].text)
        assert "chunks" in mpep_data
        
        # Step 3: Switch to case law assistant
        case_law_args = {
            "assistant_name": "case-law-assistant",
            "model": "claude-3-5-sonnet"
        }

        with patch('src.server.AssistantClientManager.update_configuration') as mock_update, \
             patch('src.server.AssistantClientManager.get_client') as mock_get_client:
            mock_update.return_value = {
                "status": "success",
                "changes": {"assistant_name": {"old": "mpep-assistant", "new": "case-law-assistant"}},
                "current_config": {
                    "assistant_name": "case-law-assistant",
                    "assistant_host": "https://test.pinecone.io",
                    "model": "claude-3-5-sonnet"
                }
            }
            mock_get_client.return_value = mock_full_environment['_client']

            case_response = await call_tool("update_configuration", case_law_args)
            assert "case-law-assistant" in case_response[0].text

    @pytest.mark.asyncio
    async def test_error_recovery_workflow(self, mock_full_environment):
        """Test error recovery and fallback scenarios."""
        
        # Test network error recovery
        mock_full_environment['_client'].context.side_effect = [
            Exception("Network timeout"),  # First call fails
            {  # Second call succeeds (simulating retry)
                "chunks": [{"text": "Recovered data", "score": 0.9}],
                "usage": {"context_tokens": 100}
            }
        ]
        
        args = {
            "query": "test query with network issues",
            "top_k": 3
        }
        
        # First call should handle error gracefully
        response = await call_tool("assistant_context", args)
        # Check for structured error response
        error_data = json.loads(response[0].text)
        assert error_data["error"] is True
        assert error_data["code"] == "INTERNAL_ERROR"
        
        # Reset side effect for second call
        mock_full_environment['_client'].context.side_effect = None
        mock_full_environment['_client'].context.return_value = {
            "chunks": [{"text": "Recovered data", "score": 0.9}],
            "usage": {"context_tokens": 100}
        }
        
        # Second call should succeed
        response = await call_tool("assistant_context", args)
        data = json.loads(response[0].text)
        assert "chunks" in data
        assert data["chunks"][0]["text"] == "Recovered data"

    @pytest.mark.asyncio
    async def test_token_optimization_workflow(self, mock_full_environment):
        """Test token cost optimization strategies."""
        
        # Test context-only approach (lowest cost)
        context_args = {
            "query": "patent eligibility analysis",
            "top_k": 5,
            "snippet_size": 1024
        }
        
        context_response = await call_tool("assistant_context", context_args)
        context_data = json.loads(context_response[0].text)
        
        # Should use only context tokens (free tier allocation)
        assert "usage" in context_data
        assert context_data["usage"]["context_tokens"] == 800
        
        # Test strategic context approach (medium cost)
        strategic_context_args = {
            "query": "patent eligibility analysis",
            "domain": "core_examination_framework", 
            "top_k": 3,
            "snippet_size": 1024
        }
        
        strategic_context_response = await call_tool("assistant_strategic_multi_search_context", strategic_context_args)
        strategic_context_data = json.loads(strategic_context_response[0].text)
        
        # Should aggregate multiple context searches
        assert "results" in strategic_context_data
        assert "total_usage" in strategic_context_data
        
        # Test full AI approach (highest cost) - use only when needed
        ai_args = {
            "query": "patent eligibility analysis", 
            "domain": "core_examination_framework",
            "max_searches": 1,  # Limit to reduce cost
            "model": "gpt-4o"
        }
        
        ai_response = await call_tool("assistant_strategic_multi_search_chat", ai_args)
        ai_data = json.loads(ai_response[0].text)
        
        # Should include both input and output token costs
        assert ai_data["total_usage"]["input_tokens"] == 2400
        assert ai_data["total_usage"]["output_tokens"] == 600


if __name__ == "__main__":
    pytest.main([__file__, "-v"])