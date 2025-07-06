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
    current_config, config_path = config.get_config()
    
    scope = "local" if config_path == config.LOCAL_CONFIG_FILE else "global"
    
    click.echo(f"--- Active ModelForge Config ({scope}) ---")
    click.echo(f"Location: {config_path}\n")

    if not current_config.get("providers"):
        click.echo("Configuration is empty. Use 'modelforge config add' to add a model.")
        return
    
    click.echo(json.dumps(current_config, indent=4))

@config_group.command(name="migrate")
def migrate_config():
    """Migrates the configuration from the old location to the new one."""
    config.migrate_old_config()

@config_group.command(name="add")
@click.option('--provider', required=True, help="The name of the provider (e.g., 'openai', 'ollama', 'github_copilot', 'google').")
@click.option('--model', required=True, help="A local, memorable name for the model (e.g., 'copilot-chat').")
@click.option('--api-model-name', help="The actual model name the API expects (e.g., 'claude-3.7-sonnet-thought').")
@click.option('--api-key', help="The API key for the provider, if applicable.")
@click.option('--dev-auth', is_flag=True, help="Use device authentication flow, if applicable.")
@click.option('--local', is_flag=True, help="Save to local project config (./model-forge/config.json).")
def add_model(provider, model, api_model_name, api_key, dev_auth, local):
    """Adds or updates a model configuration."""
    target_config_path = config.get_config_path(local=True) if local else config.GLOBAL_CONFIG_FILE
    current_config, _ = config.get_config_from_path(target_config_path)

    providers = current_config.setdefault("providers", {})
    provider_data = providers.setdefault(provider, {"models": {}})

    # --- This is a simplified logic block. We can make this more robust later ---
    if provider == "ollama":
        provider_data["llm_type"] = "ollama"
        # Use the environment variable if it exists, otherwise default to localhost.
        provider_data["base_url"] = os.getenv("OLLAMA_HOST", "http://localhost:11434")
        provider_data["auth_strategy"] = "local"
    elif provider == "openai":
        provider_data["llm_type"] = "openai_compatible"
        provider_data["base_url"] = "https://api.openai.com/v1"  # Default OpenAI endpoint
        provider_data["auth_strategy"] = "api_key"
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
    config.save_config(current_config, local=local)

    scope_msg = "local" if local else "global"
    click.echo(f"Successfully configured model '{model}' for provider '{provider}' in the {scope_msg} config.")
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

@config_group.command(name="use")
@click.option('--provider', 'provider_name', required=True, help="The name of the provider.")
@click.option('--model', 'model_alias', required=True, help="The alias of the model to use.")
@click.option('--local', is_flag=True, help="Set the current model in the local project config.")
def use_model(provider_name, model_alias, local):
    """Sets the currently active model for testing."""
    config.set_current_model(provider_name, model_alias, local=local)

@config_group.command(name="remove")
@click.option('--provider', required=True, help="The name of the provider.")
@click.option('--model', required=True, help="The alias of the model to remove.")
@click.option('--keep-credentials', is_flag=True, help="Keep stored credentials (don't remove from keyring).")
@click.option('--local', is_flag=True, help="Remove from the local project config.")
def remove_model(provider, model, keep_credentials, local):
    """Removes a model configuration and optionally its stored credentials."""
    target_config_path = config.get_config_path(local=True) if local else config.GLOBAL_CONFIG_FILE
    current_config, _ = config.get_config_from_path(target_config_path)
    
    if not _.exists():
        scope = "local" if local else "global"
        click.echo(f"Error: {scope} configuration file does not exist at {target_config_path}.")
        return
        
    providers = current_config.get("providers", {})
    
    if provider not in providers:
        click.echo(f"Error: Provider '{provider}' not found in configuration.")
        return
    
    provider_data = providers[provider]
    models = provider_data.get("models", {})
    
    if model not in models:
        click.echo(f"Error: Model '{model}' not found for provider '{provider}'.")
        return
    
    # Remove the model from configuration
    del models[model]
    
    # If no models left for this provider, remove the entire provider
    if not models:
        del providers[provider]
        click.echo(f"Removed provider '{provider}' (no models remaining).")
    else:
        click.echo(f"Removed model '{model}' from provider '{provider}'.")
    
    # Check if this was the currently selected model
    current_model = current_config.get("current_model", {})
    if (current_model.get("provider") == provider and 
        current_model.get("model") == model):
        current_config["current_model"] = {}
        click.echo("Cleared current model selection (removed model was selected).")
    
    # Save the updated configuration
    config.save_config(current_config, local=local)
    
    # Remove stored credentials unless explicitly kept
    if not keep_credentials:
        try:
            import keyring
            # Try different credential storage patterns
            credential_keys = [
                f"{provider}_{model}",
                f"{provider}:{model}",
                f"{provider}_user"
            ]
            
            removed_credentials = False
            for key in credential_keys:
                try:
                    stored_credential = keyring.get_password(provider, key)
                    if stored_credential:
                        keyring.delete_password(provider, key)
                        removed_credentials = True
                        click.echo(f"Removed stored credentials for {provider}:{key}")
                except Exception:
                    # Credential might not exist, continue
                    pass
            
            if not removed_credentials:
                click.echo("No stored credentials found to remove.")
                
        except Exception as e:
            click.echo(f"Warning: Could not remove credentials from keyring: {e}")
    else:
        click.echo("Kept stored credentials (--keep-credentials flag used).")

@cli.command(name="test")
@click.option('--prompt', required=True, help="The prompt to send to the model.")
@click.option('--verbose', is_flag=True, help="Enable verbose debug output.")
@click.option('--smart-retry', is_flag=True, help="Enable smart retry with exponential backoff for rate limiting (GitHub Copilot only).")
def test_model(prompt, verbose, smart_retry):
    """Tests the currently selected model with a prompt."""
    
    current_model = config.get_current_model()
    if not current_model:
        print("Error: No model selected. Use 'modelforge config use'.")
        return

    provider_name = current_model.get("provider")
    model_alias = current_model.get("model")

    print(f"Sending prompt to the selected model [{provider_name}/{model_alias}]...")

    # Step 1: Instantiate the registry and get the model
    registry = ModelForgeRegistry(verbose=verbose)
    llm = registry.get_llm() # Gets the currently selected model

    if not llm:
        click.echo("Failed to instantiate the language model. Check logs for details.")
        return

    try:
        # Step 2: Create the prompt and chain
        prompt_template = ChatPromptTemplate.from_messages([("human", "{input}")])
        chain = prompt_template | llm | StrOutputParser()

        # Step 3: Run the chain with smart retry if enabled
        if smart_retry and provider_name == "github_copilot":
            response = _invoke_with_smart_retry(chain, {"input": prompt}, verbose)
        else:
            response = chain.invoke({"input": prompt})
        
        print(response)

    except Exception as e:
        click.echo(f"\nAn error occurred while running the model: {e}")

def _invoke_with_smart_retry(chain, input_data, verbose=False, max_retries=3):
    """
    Invoke a LangChain chain with smart retry logic for GitHub Copilot rate limiting.
    """
    import time
    import random
    
    last_exception = None
    
    for attempt in range(max_retries):
        try:
            if attempt > 0 and verbose:
                print(f"🔄 Retry attempt {attempt + 1}/{max_retries} for GitHub Copilot...")
            
            return chain.invoke(input_data)
            
        except Exception as e:
            last_exception = e
            error_msg = str(e).lower()
            
            # Check if this is a rate limiting error that we should retry
            if any(phrase in error_msg for phrase in ["forbidden", "rate limit", "too many requests"]):
                if attempt < max_retries - 1:  # Don't sleep on the last attempt
                    # Exponential backoff with jitter: 1s, 2s, 4s + random(0-1)
                    delay = (2 ** attempt) + random.uniform(0, 1)
                    
                    if verbose:
                        print(f"⏳ Rate limited by GitHub Copilot. Waiting {delay:.1f}s before retry...")
                    
                    time.sleep(delay)
                    continue
                else:
                    if verbose:
                        print(f"❌ Max retries ({max_retries}) reached for GitHub Copilot rate limiting")
            else:
                # Non-rate-limit error, don't retry
                raise e
    
    # If we get here, all retries failed
    raise last_exception

if __name__ == '__main__':
    cli() 