import pytest
from modelforge.registry import ModelForgeRegistry
from modelforge import config

# --- Test for Ollama (No Auth) ---
def test_get_llm_ollama_success(mocker):
    """
    Tests the happy path for retrieving a local Ollama model instance.
    """
    # Arrange
    # 1. Mock the LangChain class
    mock_chat_ollama = mocker.patch('modelforge.registry.ChatOllama')

    # 2. Set up the configuration
    ollama_config = {
        "providers": {
            "ollama": {
                "llm_type": "ollama",
                "base_url": "http://localhost:11434",
                "auth_strategy": "local",
                "models": {
                    "qwen3:1.7b": {}
                }
            }
        }
    }
    config.save_config(ollama_config)
    config.set_current_model("ollama", "qwen3:1.7b")

    # Act
    registry = ModelForgeRegistry()
    llm_instance = registry.get_llm()

    # Assert
    assert llm_instance is not None
    mock_chat_ollama.assert_called_once_with(
        model="qwen3:1.7b",
        base_url="http://localhost:11434"
    )

# --- Test for OpenAI Compatible (API Key Auth) ---
def test_get_llm_openai_compatible_success(mocker):
    """
    Tests the happy path for retrieving an OpenAI-compatible model instance.
    """
    # Arrange
    # 1. Mock the auth and LangChain components
    mock_get_credentials = mocker.patch('modelforge.auth.get_credentials')
    mock_chat_openai = mocker.patch('modelforge.registry.ChatOpenAI')

    # 2. Mock the return value for credentials
    mock_get_credentials.return_value = {"api_key": "test-secret-key"}

    # 3. Set up the configuration
    openai_config = {
        "providers": {
            "openai": {
                "llm_type": "openai_compatible",
                "base_url": "https://api.openai.com/v1",
                "auth_strategy": "api_key",
                "models": {
                    "gpt-4o-mini": {
                        "api_model_name": "gpt-4o-mini-2024-07-18"
                    }
                }
            }
        }
    }
    config.save_config(openai_config)
    config.set_current_model("openai", "gpt-4o-mini")

    # Act
    registry = ModelForgeRegistry()
    llm_instance = registry.get_llm()

    # Assert
    assert llm_instance is not None
    mock_get_credentials.assert_called_once_with("openai", "gpt-4o-mini", verbose=False)
    mock_chat_openai.assert_called_once_with(
        model_name="gpt-4o-mini-2024-07-18",
        api_key="test-secret-key",
        base_url="https://api.openai.com/v1"
    ) 