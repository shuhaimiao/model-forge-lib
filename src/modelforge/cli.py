import click
import json
import os
from . import config
from . import auth
from .registry import ModelForgeRegistry

# Import LangChain components
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_openai import ChatOpenAI
from langchain_community.chat_models import ChatOllama

@click.group()
def cli():
    """A CLI for managing the Model Forge library."""
    pass

@cli.group(name="config")
def config_group():
    """Commands for managing the model configuration."""
    pass

@config_group.command(name="show")
def show_config():
    """Displays the current model configuration."""
    current_config = config.get_config()
    if not current_config.get("providers"):
        click.echo("Configuration is empty. Use 'modelforge config add' to add a model.")
        return
    
    click.echo(json.dumps(current_config, indent=4))

@config_group.command(name="add")
@click.option('--provider', required=True, help="The name of the provider (e.g., 'ollama', 'github_copilot').")
@click.option('--model', required=True, help="A local, memorable name for the model (e.g., 'copilot-chat').")
@click.option('--api-model-name', help="The actual model name the API expects (e.g., 'claude-3.7-sonnet-thought').")
@click.option('--api-key', help="The API key for the provider, if applicable.")
@click.option('--dev-auth', is_flag=True, help="Use device authentication flow, if applicable.")
def add_model(provider, model, api_model_name, api_key, dev_auth):
    """Adds or updates a model configuration."""
    current_config = config.get_config()
    providers = current_config.setdefault("providers", {})
    provider_data = providers.setdefault(provider, {"models": {}})

    # --- This is a simplified logic block. We can make this more robust later ---
    if provider == "ollama":
        provider_data["llm_type"] = "ollama"
        # Use the environment variable if it exists, otherwise default to localhost.
        provider_data["base_url"] = os.getenv("OLLAMA_HOST", "http://localhost:11434")
        provider_data["auth_strategy"] = "local"
    elif provider == "github_copilot":
        provider_data["llm_type"] = "openai_compatible"
        provider_data["base_url"] = "https://api.githubcopilot.com"
        provider_data["auth_strategy"] = "device_flow"
        provider_data["auth_details"] = {
            "client_id": "01ab8ac9400c4e429b23", # From VS Code's public source
            "device_code_url": "https://github.com/login/device/code",
            "token_url": "https://github.com/login/oauth/access_token",
            "scope": "read:user"
        }
    elif provider == "google":
        provider_data["llm_type"] = "google_genai"
        provider_data["auth_strategy"] = "api_key"
    elif api_key:
        # This can be a generic API key provider in the future
        click.echo(f"Error: Unsupported provider '{provider}' for API key auth.")
        return

    model_config = {}
    if api_model_name:
        model_config["api_model_name"] = api_model_name

    provider_data["models"][model] = model_config
    config.save_config(current_config)

    click.echo(f"Successfully configured model '{model}' for provider '{provider}'.")
    click.echo("Run 'modelforge config show' to see the updated configuration.")

    # Optionally, trigger authentication immediately
    if dev_auth:
        auth_handler = auth.DeviceFlowAuth(
            provider_name=provider,
            **provider_data["auth_details"]
        )
        auth_handler.authenticate()
    elif api_key:
        auth_handler = auth.ApiKeyAuth(provider)
        # We don't call authenticate() here because the key is already provided.
        # We can store it directly.
        import keyring
        keyring.set_password(provider, f"{provider}_user", api_key)
        click.echo(f"API key for {provider} has been stored securely.")

@config_group.command(name="select")
@click.option('--provider', 'provider_name', required=True, help="The name of the provider.")
@click.option('--model', 'model_alias', required=True, help="The alias of the model to select.")
def select_model(provider_name, model_alias):
    """Sets the currently active model for testing."""
    config.set_current_model(provider_name, model_alias)

@cli.command(name="test")
@click.option('--prompt', required=True, help="The prompt to send to the model.")
def test_model(prompt):
    """Tests the currently selected model with a prompt."""
    
    current_model = config.get_current_model()
    if not current_model:
        print("Error: No model selected. Use 'modelforge config select'.")
        return

    provider_name = current_model.get("provider")
    model_alias = current_model.get("model")

    print(f"Sending prompt to the selected model [{provider_name}/{model_alias}]...")

    # Step 1: Instantiate the registry and get the model
    registry = ModelForgeRegistry()
    llm = registry.get_llm() # Gets the currently selected model

    if not llm:
        click.echo("Failed to instantiate the language model. Check logs for details.")
        return

    try:
        # Step 2: Create the prompt and chain
        prompt_template = ChatPromptTemplate.from_messages([("human", "{input}")])
        chain = prompt_template | llm | StrOutputParser()

        # Step 3: Run the chain and print the output
        response = chain.invoke({"input": prompt})
        print(response)

    except Exception as e:
        click.echo(f"\nAn error occurred while running the model: {e}")

if __name__ == '__main__':
    cli() 