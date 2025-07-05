from typing import Optional, Dict, Any
from . import config, auth

# LangChain components
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_openai import ChatOpenAI
from langchain_community.chat_models import ChatOllama
from langchain_google_genai import ChatGoogleGenerativeAI


class ModelForgeRegistry:
    """
    A factory for creating and managing LLM instances from a central configuration.
    """

    def __init__(self):
        self._config = config.get_config()

    def get_llm(self, provider_name: Optional[str] = None, model_alias: Optional[str] = None) -> Optional[BaseChatModel]:
        """
        Retrieves and initializes a LangChain chat model based on the configuration.

        If provider_name and model_alias are provided, it uses them. Otherwise, it
        falls back to the currently selected model in the config.

        Returns:
            An initialized LangChain BaseChatModel, or None if configuration is missing or invalid.
        """
        if not provider_name or not model_alias:
            current_model = config.get_current_model()
            if not current_model:
                print("Error: No model selected. Use 'modelforge config select' or provide provider and model.")
                return None
            provider_name = current_model.get("provider")
            model_alias = current_model.get("model")

        provider_data = self._config.get("providers", {}).get(provider_name)
        if not provider_data:
            print(f"Error: Provider '{provider_name}' not found in configuration.")
            return None

        model_data = provider_data.get("models", {}).get(model_alias)
        if model_data is None: # Can be an empty dict
            print(f"Error: Model '{model_alias}' not found for provider '{provider_name}'.")
            return None
            
        llm_type = provider_data.get("llm_type")
        auth_strategy_name = provider_data.get("auth_strategy")

        try:
            if llm_type == "ollama":
                return ChatOllama(model=model_alias)

            elif llm_type == "openai_compatible":
                credentials = auth.get_credentials(provider_name, model_alias)
                if not credentials:
                    return None
                
                api_key = credentials.get("access_token") or credentials.get("api_key")
                if not api_key:
                    print(f"Error: Could not find token or key for '{provider_name}'.")
                    return None

                return ChatOpenAI(
                    model_name=model_data.get("api_model_name", model_alias),
                    api_key=api_key,
                    base_url=provider_data.get("base_url")
                )

            elif llm_type == "google_genai":
                credentials = auth.get_credentials(provider_name, model_alias)
                if not credentials:
                    return None

                api_key = credentials.get("api_key")
                if not api_key:
                    print(f"Error: Could not find API key for '{provider_name}'.")
                    return None

                return ChatGoogleGenerativeAI(
                    model=model_data.get("api_model_name", model_alias),
                    google_api_key=api_key
                )

            else:
                print(f"Error: Unsupported llm_type '{llm_type}' for provider '{provider_name}'.")
                return None

        except Exception as e:
            print(f"Error creating LLM instance for {provider_name}/{model_alias}: {e}")
            return None