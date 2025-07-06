import pytest
from unittest.mock import patch, mock_open
import json
from pathlib import Path

# Module to be tested
from modelforge import config

# Use a dummy file path for testing
DUMMY_CONFIG_PATH = Path("/tmp/test_config.json")

def test_get_config_creates_new_file_if_not_exists():
    """
    Verify that get_config() creates a new, empty config file if one doesn't exist.
    """
    # Act
    config_data = config.get_config()

    # Assert
    assert DUMMY_CONFIG_PATH.exists()
    assert config_data == {}
    with open(DUMMY_CONFIG_PATH, 'r') as f:
        assert json.load(f) == {}

def test_save_and_get_config():
    """
    Verify that save_config() writes data and get_config() reads it correctly.
    """
    # Arrange
    test_data = {"providers": {"test_provider": {"models": {"test_model": {}}}}}

    # Act
    config.save_config(test_data)
    read_data = config.get_config()

    # Assert
    assert read_data == test_data

def test_set_and_get_current_model():
    """
    Verify that a model can be set as current and then retrieved.
    """
    # Arrange
    initial_config = {
        "providers": {
            "test_provider": {
                "models": {
                    "model-1": {},
                    "model-2": {}
                }
            }
        }
    }
    config.save_config(initial_config)

    # Act
    success = config.set_current_model("test_provider", "model-2")
    current_model = config.get_current_model()

    # Assert
    assert success is True
    assert current_model == {"provider": "test_provider", "model": "model-2"}
    
    # Verify the underlying config file was updated
    full_config = config.get_config()
    assert full_config["current_model"] == {"provider": "test_provider", "model": "model-2"}

def test_set_current_model_fails_for_nonexistent_model():
    """
    Verify that setting a non-existent model as current fails gracefully.
    """
    # Arrange
    initial_config = {
        "providers": {
            "test_provider": {
                "models": {
                    "model-1": {}
                }
            }
        }
    }
    config.save_config(initial_config)
    
    # Act
    success = config.set_current_model("test_provider", "non_existent_model")
    current_model = config.get_current_model()

    # Assert
    assert success is False
    assert current_model is None # It should not have been set 