import pytest
from unittest.mock import patch
import json
from pathlib import Path

# Module to be tested
from modelforge import config

def test_get_config_creates_global_if_none_exist():
    """Verify get_config() creates a new global config if no file exists."""
    config_data, config_path = config.get_config()
    assert config.GLOBAL_CONFIG_FILE.exists()
    assert config_path == config.GLOBAL_CONFIG_FILE
    assert config_data == {}

def test_get_config_prefers_local_over_global():
    """Verify get_config() returns local config if both exist."""
    # Arrange
    global_data = {"providers": {"global": {}}}
    local_data = {"providers": {"local": {}}}
    config.save_config(global_data, local=False)
    config.save_config(local_data, local=True)

    # Act
    read_data, read_path = config.get_config()

    # Assert
    assert read_path == config.LOCAL_CONFIG_FILE
    assert read_data == local_data

def test_save_and_get_local_config():
    """Verify saving to and getting from a local config works."""
    # Arrange
    test_data = {"providers": {"local_provider": {}}}

    # Act
    config.save_config(test_data, local=True)
    read_data, _ = config.get_config()

    # Assert
    assert config.LOCAL_CONFIG_FILE.exists()
    assert read_data == test_data

def test_set_current_model_in_local_config():
    """Verify setting the current model in the local config."""
    # Arrange
    initial_config = {"providers": {"test": {"models": {"test-model": {}}}}}
    config.save_config(initial_config, local=True)

    # Act
    success = config.set_current_model("test", "test-model", local=True)
    current_model = config.get_current_model()
    
    # Assert
    assert success is True
    assert current_model == {"provider": "test", "model": "test-model"}
    
    # Check that only the local file was modified
    local_config, _ = config.get_config_from_path(config.LOCAL_CONFIG_FILE)
    global_config, _ = config.get_config_from_path(config.GLOBAL_CONFIG_FILE)
    
    assert "current_model" in local_config
    assert "current_model" not in global_config