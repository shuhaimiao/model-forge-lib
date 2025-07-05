import click
import json
from . import config
from . import auth

@click.group()
def cli():
    """A CLI for managing the Model Forge library configuration."""
    pass

@cli.command()
def show():
    """Displays the current model configuration."""
    current_config = config.get_config()
    if not current_config:
        click.echo("Configuration is empty. Use 'modelforge config add' to add a model.")
        return
    
    click.echo(json.dumps(current_config, indent=4))

@cli.command()
@click.option('--provider', required=True, help="The name of the provider (e.g., 'ollama', 'github_copilot').")
@click.option('--model', required=True, help="The name of the model (e.g., 'qwen3:1.7b').")
@click.option('--api-key', help="The API key for the provider, if applicable.")
@click.option('--dev-auth', is_flag=True, help="Use device authentication flow, if applicable.")
def add(provider, model, api_key, dev_auth):
    """Adds or updates a model configuration."""
    current_config = config.get_config()
    providers = current_config.setdefault("providers", {})
    provider_data = providers.setdefault(provider, {"models": {}})

    # --- This is a simplified logic block. We can make this more robust later ---
    if provider == "ollama":
        provider_data["llm_type"] = "ollama"
        provider_data["base_url"] = "http://localhost:11434" # A sensible default
        provider_data["auth_strategy"] = "local"
    elif provider == "github_copilot":
        provider_data["llm_type"] = "openai_compatible"
        provider_data["base_url"] = "https://api.githubcopilot.com"
        provider_data["auth_strategy"] = "device_flow"
        provider_data["auth_details"] = {
            "client_id": "Iv1.b507a08c87ecfe98", # This is a public client_id for Copilot
            "device_code_url": "https://github.com/login/device/code",
            "token_url": "https://github.com/login/oauth/token",
            "scope": "copilot"
        }
    elif api_key:
        provider_data["llm_type"] = "openai_compatible" # Assuming for now
        provider_data["auth_strategy"] = "api_key"
    else:
        click.echo(f"Error: Unsupported provider '{provider}' or missing authentication method.")
        return

    provider_data["models"][model] = {}
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

if __name__ == '__main__':
    cli() 