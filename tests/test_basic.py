"""Basic tests for USPTO Pinecone Assistant MCP."""

import pytest
from unittest.mock import Mock, patch
from pydantic import ValidationError
from src.config.config import Settings
from src.models.models import Message, AssistantChatParams, StrategySearchParams, AssistantContextParams, EvaluateAnswerParams
from src.services.strategic_search import StrategySearchProcessor


class TestConfiguration:
    """Test configuration validation and settings."""
    
    def test_settings_validation_success(self):
        """Test successful settings validation."""
        settings_data = {
            "pinecone_assistant_api_key": "pcsk_test_key_12345678901234567890abcdef",
            "pinecone_assistant_host": "https://test.pinecone.io",
            "pinecone_assistant_name": "test-assistant"
        }

        settings = Settings(**settings_data)

        assert settings.pinecone_assistant_api_key == "pcsk_test_key_12345678901234567890abcdef"
        assert settings.pinecone_assistant_host == "https://test.pinecone.io"
        assert settings.pinecone_assistant_name == "test-assistant"
        assert settings.pinecone_assistant_model == "gpt-4o"  # default
    
    def test_api_key_validation_failure(self):
        """Test API key validation failure."""
        with pytest.raises(ValueError, match="Invalid Pinecone Assistant API key format"):
            Settings(
                pinecone_assistant_api_key="invalid_key",
                pinecone_assistant_host="https://test.pinecone.io",
                pinecone_assistant_name="test-assistant"
            )
    
    def test_base_url_property(self):
        """Test base URL construction."""
        settings = Settings(
            pinecone_assistant_api_key="pcsk_test_key_12345678901234567890abcdef",
            pinecone_assistant_host="https://test.pinecone.io",
            pinecone_assistant_name="test-assistant"
        )
        
        expected_url = "https://test.pinecone.io/assistant/chat/test-assistant"
        assert settings.base_url == expected_url
    
    def test_is_valid_model(self):
        """Test model validation."""
        settings = Settings(
            pinecone_assistant_api_key="pcsk_test_key_12345678901234567890abcdef",
            pinecone_assistant_host="https://test.pinecone.io", 
            pinecone_assistant_name="test-assistant"
        )
        
        assert settings.is_valid_model("gpt-4o") is True
        assert settings.is_valid_model("claude-3-5-sonnet") is True
        assert settings.is_valid_model("invalid-model") is False


class TestTypes:
    """Test Pydantic model validation."""
    
    def test_message_creation(self):
        """Test Message model creation."""
        message = Message(role="user", content="Test message")
        
        assert message.role == "user"
        assert message.content == "Test message"
    
    def test_assistant_chat_params(self):
        """Test AssistantChatParams validation."""
        messages = [Message(role="user", content="Test")]
        params = AssistantChatParams(
            messages=messages,
            model="gpt-4o",
            temperature=0.7,
            include_highlights=True
        )
        
        assert len(params.messages) == 1
        assert params.model == "gpt-4o"
        assert params.temperature == 0.7
        assert params.include_highlights is True
    
    def test_strategy_search_params(self):
        """Test StrategySearchParams validation."""
        params = StrategySearchParams(
            query="test query",
            domain="patent_law",
            max_searches=5,
            model="claude-3-5-sonnet"
        )

        assert params.query == "test query"
        assert params.domain == "patent_law"
        assert params.max_searches == 5
        assert params.model == "claude-3-5-sonnet"

    def test_evaluate_answer_params(self):
        """Test EvaluateAnswerParams validation."""
        params = EvaluateAnswerParams(
            question="What is the Alice two-step test?",
            answer="The Alice test has two steps...",
            ground_truth_answer="Alice Corp v. CLS Bank established a two-part test..."
        )

        assert params.question == "What is the Alice two-step test?"
        assert params.answer == "The Alice test has two steps..."
        assert params.ground_truth_answer == "Alice Corp v. CLS Bank established a two-part test..."

    def test_evaluate_answer_params_missing_fields(self):
        """Test EvaluateAnswerParams raises ValidationError when required fields are missing."""
        with pytest.raises(ValidationError):
            EvaluateAnswerParams(answer="some answer", ground_truth_answer="some truth")

        with pytest.raises(ValidationError):
            EvaluateAnswerParams(question="some question", ground_truth_answer="some truth")

        with pytest.raises(ValidationError):
            EvaluateAnswerParams(question="some question", answer="some answer")

    def test_assistant_context_params_multimodal(self):
        """Test AssistantContextParams accepts multimodal and include_binary_content fields."""
        params = AssistantContextParams(
            query="test query",
            multimodal=False,
            include_binary_content=False
        )

        assert params.query == "test query"
        assert params.multimodal is False
        assert params.include_binary_content is False

    def test_assistant_context_params_multimodal_defaults(self):
        """Test AssistantContextParams multimodal fields default to None (API chooses)."""
        params = AssistantContextParams(query="test query")

        assert params.multimodal is None
        assert params.include_binary_content is None

    def test_assistant_context_params_requires_query_or_messages(self):
        """Test AssistantContextParams validator rejects neither query nor messages."""
        with pytest.raises(ValidationError, match="Either 'query' or 'messages' is required"):
            AssistantContextParams()

    def test_assistant_context_params_messages_without_query(self):
        """Test AssistantContextParams accepts messages as alternative to query."""
        params = AssistantContextParams(
            messages=[{"role": "user", "content": "What is Section 101?"}]
        )

        assert params.query is None
        assert len(params.messages) == 1
        assert params.messages[0]["content"] == "What is Section 101?"


class TestStrategicSearch:
    """Test strategic search functionality."""
    
    @pytest.fixture
    def search_processor(self, tmp_path):
        """Create a test search processor with mock YAML."""
        yaml_content = """
patent_law:
  searches:
    - name: "test_search"
      query: "Test query for {primary} and {key_terms}"
      description: "Test search pattern"
      enabled: true
    - name: "disabled_search"
      query: "Disabled {primary}"
      description: "Disabled search"
      enabled: false
        """
        
        yaml_file = tmp_path / "test_searches.yaml"
        yaml_file.write_text(yaml_content)
        
        return StrategySearchProcessor(yaml_file)
    
    def test_load_patterns(self, search_processor):
        """Test pattern loading from YAML."""
        domains = search_processor.get_available_domains()
        assert "patent_law" in domains
        
        searches = search_processor.get_domain_searches("patent_law")
        assert len(searches) == 1  # Only enabled search
        assert searches[0].name == "test_search"
    
    def test_extract_key_terms(self, search_processor):
        """Test key term extraction."""
        from src.util.text_utils import extract_key_terms

        query = "What are the requirements for software patent eligibility?"
        key_terms = extract_key_terms(query, max_terms=5)

        assert "requirements" in key_terms
        assert "software" in key_terms
        assert "patent" in key_terms
        assert "eligibility" in key_terms
        # Should exclude stop words like "are", "the", "for"
        assert "are" not in key_terms
        assert "the" not in key_terms
    
    def test_substitute_patterns(self, search_processor):
        """Test pattern substitution."""
        query = "software patent eligibility"
        patterns = search_processor.substitute_patterns(query, "patent_law")
        
        assert len(patterns) == 1
        pattern = patterns[0]
        
        assert pattern["name"] == "test_search"
        assert "software patent eligibility" in pattern["query"]
        assert "software patent eligibility" in pattern["query"]  # {primary} substitution
        # Should contain key terms
        assert any(term in pattern["query"] for term in ["software", "patent", "eligibility"])
    
    def test_validate_domain(self, search_processor):
        """Test domain validation."""
        assert search_processor.validate_domain("patent_law") is True
        assert search_processor.validate_domain("invalid_domain") is False


class TestAssistantClientMock:
    """Test assistant client with mocking."""
    
    @patch('src.api.assistant_client.Pinecone')
    def test_client_initialization(self, mock_pinecone):
        """Test client initialization."""
        from src.api.assistant_client import PineconeAssistantClient

        settings = Settings(
            pinecone_assistant_api_key="pcsk_test_key_12345678901234567890abcdef",
            pinecone_assistant_host="https://test.pinecone.io",
            pinecone_assistant_name="test-assistant"
        )
        
        client = PineconeAssistantClient(settings)
        client.initialize()
        
        # Verify Pinecone was called with correct API key
        mock_pinecone.assert_called_once_with(api_key="pcsk_test_key_12345678901234567890abcdef")
    
    @patch('src.api.assistant_client.Pinecone')
    def test_chat_request(self, mock_pinecone):
        """Test chat request handling."""
        from src.api.assistant_client import PineconeAssistantClient
        
        # Mock the assistant response
        mock_response = Mock()
        mock_response.model_dump.return_value = {
            "finish_reason": "stop",
            "message": {
                "role": "assistant",
                "content": "Test response"
            },
            "citations": []
        }
        
        mock_assistant = Mock()
        mock_assistant.chat.return_value = mock_response
        
        mock_pc = Mock()
        mock_pc.assistant.Assistant.return_value = mock_assistant
        mock_pinecone.return_value = mock_pc
        
        settings = Settings(
            pinecone_assistant_api_key="pcsk_test_key_12345678901234567890abcdef",
            pinecone_assistant_host="https://test.pinecone.io",
            pinecone_assistant_name="test-assistant"
        )

        client = PineconeAssistantClient(settings)
        client.initialize()

        # Test chat request
        params = AssistantChatParams(
            messages=[Message(role="user", content="Test question")]
        )
        
        response = client.chat(params)
        
        # Verify response structure
        assert response["finish_reason"] == "stop"
        assert response["message"]["content"] == "Test response"
        
        # Verify assistant.chat was called
        mock_assistant.chat.assert_called_once()


if __name__ == "__main__":
    pytest.main([__file__])