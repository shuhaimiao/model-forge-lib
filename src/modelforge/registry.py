from typing import Optional, Dict, Any
from . import config, auth

# LangChain components
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_openai import ChatOpenAI
from langchain_community.chat_models import ChatOllama

class ModelForgeRegistry:
    """
    A factory for creating and managing LLM instances from a central configuration.
    """

    def __init__(self):
        self._config = config.get_config()

    def get_llm(self, provider_name: Optional[str] = None, model_alias: Optional[str] = None) -> Optional[BaseChatModel]:
        """
        Gets an instantiated LangChain chat model.

        If provider_name and model_alias are not provided, it uses the
        currently selected model from the configuration.

        Args:
            provider_name: The name of the provider (e.g., 'github_copilot').
            model_alias: The local alias for the model (e.g., 'copilot-chat').

        Returns:
            An instance of a LangChain BaseChatModel, or None if an error occurs.
        """
        if not provider_name or not model_alias:
            current_model_info = config.get_current_model()
            if not current_model_info:
                print("Error: No model specified and no model is currently selected.")
                print("Use 'modelforge config select' or provide provider_name and model_alias.")
                return None
            provider_name = current_model_info["provider"]
            model_alias = current_model_info["model"]

        provider_data = self._config.get("providers", {}).get(provider_name)
        if not provider_data:
            print(f"Error: Configuration for provider '{provider_name}' not found.")
            return None

        model_config = provider_data.get("models", {}).get(model_alias)
        if model_config is None:
            print(f"Error: Configuration for model '{model_alias}' not found.")
            return None

        auth_strategy_name = provider_data.get("auth_strategy")
        llm = None

        try:
            if auth_strategy_name == "local":
                llm = ChatOllama(model=model_alias)
                print(f"Successfully instantiated local model '{model_alias}'.")
                return llm

            elif auth_strategy_name in ["device_flow", "api_key"]:
                auth_class = getattr(auth, auth_strategy_name.replace("_", " ").title().replace(" ", "") + "Auth")
                
                if auth_strategy_name == "device_flow":
                    auth_handler = auth_class(provider_name=provider_name, **provider_data["auth_details"])
                else:
                    auth_handler = auth_class(provider_name=provider_name)
                
                creds = auth_handler.get_credentials()
                if not creds:
                    print(f"Error: Could not retrieve credentials for {provider_name}.")
                    print("Please run 'modelforge config add' to authenticate.")
                    return None
                
                api_key = creds.get("access_token") or creds.get("api_key")

                llm = ChatOpenAI(
                    model=model_config.get("api_model_name", model_alias),
                    api_key=api_key,
                    base_url=provider_data.get("base_url")
                )
                print(f"Successfully instantiated remote model '{model_alias}' for provider '{provider_name}'.")
                return llm
            else:
                print(f"Error: Unsupported authentication strategy '{auth_strategy_name}'.")
                return None
        except Exception as e:
            print(f"An error occurred while instantiating the model: {e}")
            return None