import os
import json
from pathlib import Path
from typing import Dict, Any, Optional, Tuple

# --- Configuration Paths ---
# Allow overriding the global config directory via an environment variable
_config_dir_override = os.environ.get("MODEL_FORGE_CONFIG_DIR")

# Global config: ~/.model-forge/config.json
GLOBAL_CONFIG_DIR = Path(_config_dir_override) if _config_dir_override else Path.home() / ".model-forge"
GLOBAL_CONFIG_FILE = GLOBAL_CONFIG_DIR / "config.json"

# Local config: ./model-forge/config.json
LOCAL_CONFIG_DIR = Path.cwd() / "model-forge"
LOCAL_CONFIG_FILE = LOCAL_CONFIG_DIR / "config.json"


def get_config_path(local: bool = False) -> Path:
    """
    Determines the path to the configuration file to be used.
    
    If `local` is True, it returns the local path. Otherwise, it returns
    the path of the active configuration (local if it exists, global otherwise).
    
    Args:
        local: If True, force the use of the local configuration path.
    
    Returns:
        The Path object for the configuration file.
    """
    if local:
        return LOCAL_CONFIG_FILE
    
    # Precedence: Local > Global
    if LOCAL_CONFIG_FILE.exists():
        return LOCAL_CONFIG_FILE
    
    return GLOBAL_CONFIG_FILE


def get_config() -> Tuple[Dict[str, Any], Path]:
    """
    Loads model configuration with local-over-global precedence.

    Returns:
        A tuple containing:
        - A dictionary of the configuration data.
        - The path of the loaded configuration file.
    """
    config_path = get_config_path()

    if not config_path.exists():
        if config_path == GLOBAL_CONFIG_FILE:
            # Create a new global config if it doesn't exist
            GLOBAL_CONFIG_DIR.mkdir(parents=True, exist_ok=True)
            save_config({}, local=False) # Explicitly save to global
            return {}, config_path
        else:
            # Local file doesn't exist, and we're not creating it automatically.
            # Fallback to checking the global file.
            return get_config_from_path(GLOBAL_CONFIG_FILE)
            
    return get_config_from_path(config_path)

def get_config_from_path(path: Path) -> Tuple[Dict[str, Any], Path]:
    """Reads a config file from a specific path."""
    if not path.exists():
        return {}, path
        
    try:
        with open(path, "r") as f:
            return json.load(f), path
    except (json.JSONDecodeError, IOError):
        print(f"Warning: Could not read or parse config file at {path}. Using empty config.")
        return {}, path


def save_config(config_data: Dict[str, Any], local: bool = False):
    """
    Saves configuration data to either the local or global file.
    
    Args:
        config_data: The configuration dictionary to save.
        local: If True, saves to the local config file. Otherwise, saves to global.
    """
    config_path = LOCAL_CONFIG_FILE if local else GLOBAL_CONFIG_FILE
    config_dir = config_path.parent

    try:
        config_dir.mkdir(parents=True, exist_ok=True)
        with open(config_path, "w") as f:
            json.dump(config_data, f, indent=4)
    except IOError as e:
        print(f"Error: Could not save config file to {config_path}. Details: {e}")


def set_current_model(provider: str, model: str, local: bool = False):
    """
    Sets the currently active model in the configuration.

    Args:
        provider: The name of the provider.
        model: The local alias of the model.
        local: If True, modifies the local configuration.
    """
    # When setting a model, we should read from the specific config file, not the merged one.
    target_config_path = get_config_path(local=local)
    config_data, _ = get_config_from_path(target_config_path)

    providers = config_data.get("providers", {})
    
    if provider not in providers or model not in providers[provider].get("models", {}):
        scope = "local" if local else "global"
        print(f"Error: Model '{model}' for provider '{provider}' not found in {scope} configuration.")
        print("Please add it using 'modelforge config add' first.")
        return False

    config_data["current_model"] = {"provider": provider, "model": model}
    save_config(config_data, local=local)
    scope_msg = "local" if local else "global"
    print(f"Successfully set '{model}' from provider '{provider}' as the current model in the {scope_msg} config.")
    return True


def get_current_model() -> Optional[Dict[str, str]]:
    """
    Retrieves the currently active model from the active configuration.

    Returns:
        A dictionary containing the provider and model alias, or None.
    """
    config_data, _ = get_config()
    return config_data.get("current_model")


def migrate_old_config():
    """
    Migrates the configuration from the old location to the new global location.
    
    Old location: ~/.config/model-forge/models.json
    New location: ~/.model-forge/config.json
    """
    old_config_dir = Path.home() / ".config" / "model-forge"
    old_config_file = old_config_dir / "models.json"

    if old_config_file.exists():
        if not GLOBAL_CONFIG_FILE.exists():
            print(f"Found old configuration at {old_config_file}.")
            print(f"Migrating to new global location: {GLOBAL_CONFIG_FILE}")
            
            # Ensure the new directory exists
            GLOBAL_CONFIG_DIR.mkdir(parents=True, exist_ok=True)
            
            # Move the file
            old_config_file.rename(GLOBAL_CONFIG_FILE)
            
            # Clean up the old directory if it's empty
            if not any(old_config_dir.iterdir()):
                old_config_dir.rmdir()
                
            print("Migration successful.")
            print(f"Your configuration is now located at {GLOBAL_CONFIG_FILE}.")
        else:
            print("Old configuration file found, but a new global configuration already exists.")
            print(f"  - Old: {old_config_file}")
            print(f"  - New: {GLOBAL_CONFIG_FILE}")
            print("Please merge them manually if needed.")
    else:
        print("No old configuration file found to migrate.") 