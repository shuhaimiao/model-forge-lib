from typing import List, Dict, Any, Optional
from langchain_core.language_models import BaseLanguageModel
from langchain_openai import ChatOpenAI
from langchain_ollama import OllamaLLM

from . import config
from . import auth

class ModelRegistry:
    """A factory for creating and managing LLM instances."""

    def __init__(self):
        self.config = config.get_config()
        self.providers = self.config.get("providers", {})

    def list_models(self) -> List[str]:
        """Returns a list of all available model IDs in the format 'provider/model_name'."""
        model_ids = []
        for provider_name, provider_data in self.providers.items():
            for model_name in provider_data.get("models", {}):
                model_ids.append(f"{provider_name}/{model_name}")
        return model_ids

    def get_model_instance(self, model_id: str) -> Optional[BaseLanguageModel]:
        """
        Gets a fully configured and authenticated LangChain model instance.

        Args:
            model_id: The unique identifier for the model (e.g., 'github_copilot/claude-3.7-sonnet').

        Returns:
            An initialized BaseLanguageModel instance, or None if the model_id is not found.
        """
        if "/" not in model_id:
            print(f"Error: Invalid model_id format. Expected 'provider/model_name', got '{model_id}'.")
            return None

        provider_name, model_name = model_id.split("/", 1)

        provider_data = self.providers.get(provider_name)
        if not provider_data:
            print(f"Error: Provider '{provider_name}' not found in configuration.")
            return None

        model_info = provider_data.get("models", {}).get(model_name)
        if model_info is None: # Can be an empty dict {}
            print(f"Error: Model '{model_name}' not found for provider '{provider_name}'.")
            return None
        
        # Determine and execute authentication strategy
        auth_strategy_name = provider_data.get("auth_strategy", "local")
        auth_handler = self._get_auth_handler(provider_name, auth_strategy_name, provider_data.get("auth_details", {}))
        
        credentials = auth_handler.get_credentials()
        if not credentials:
            try:
                credentials = auth_handler.authenticate()
            except Exception as e:
                print(f"Authentication failed for {provider_name}: {e}")
                return None

        # Instantiate the correct LangChain model
        llm_type = provider_data.get("llm_type")
        
        if llm_type == "ollama":
            return OllamaLLM(model=model_name, base_url=provider_data.get("base_url"))
        
        elif llm_type == "openai_compatible":
            api_key = credentials.get("access_token") or credentials.get("api_key")
            return ChatOpenAI(
                model_name=model_name,
                api_key=api_key,
                base_url=provider_data.get("base_url")
            )
        
        else:
            print(f"Error: Unsupported llm_type '{llm_type}' for provider '{provider_name}'.")
            return None

    def _get_auth_handler(self, provider_name: str, strategy_name: str, details: Dict[str, Any]) -> auth.AuthStrategy:
        """Factory function to get the correct authentication handler."""
        if strategy_name == "api_key":
            return auth.ApiKeyAuth(provider_name)
        elif strategy_name == "device_flow":
            return auth.DeviceFlowAuth(
                provider_name=provider_name,
                client_id=details.get("client_id"),
                device_code_url=details.get("device_code_url"),
                token_url=details.get("token_url"),
                scope=details.get("scope"),
            )
        else: # Default to "local"
            return auth.LocalAuth() 