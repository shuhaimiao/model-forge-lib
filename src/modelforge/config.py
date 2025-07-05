import os
import json
from pathlib import Path
from typing import Dict, Any

# Define the default directory and file path for the configuration
CONFIG_DIR = Path(os.path.expanduser("~")) / ".config" / "modelforge"
CONFIG_FILE = CONFIG_DIR / "models.json"

def get_config() -> Dict[str, Any]:
    """
    Loads the model configuration from the default JSON file.

    If the file or directory does not exist, it creates them with a default
    empty configuration.

    Returns:
        A dictionary containing the model configuration.
    """
    if not CONFIG_FILE.exists():
        # Create the directory if it doesn't exist
        CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        # Create a default empty config file
        save_config({})
        return {}

    try:
        with open(CONFIG_FILE, "r") as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError):
        # If file is corrupted or unreadable, return a default and log an error
        print(f"Warning: Could not read or parse config file at {CONFIG_FILE}. Using default empty config.")
        return {}

def save_config(config_data: Dict[str, Any]):
    """
    Saves the provided configuration data to the default JSON file.

    Args:
        config_data: A dictionary containing the configuration to save.
    """
    try:
        # Ensure the directory exists before writing
        CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        with open(CONFIG_FILE, "w") as f:
            json.dump(config_data, f, indent=4)
    except IOError as e:
        print(f"Error: Could not save config file to {CONFIG_FILE}. Details: {e}") 