import pytest
from click.testing import CliRunner
from modelforge.cli import cli
from modelforge import config
import json

@pytest.fixture
def runner():
    return CliRunner()

def test_config_show_empty(runner):
    """Test `modelforge config show` with an empty configuration."""
    result = runner.invoke(cli, ["config", "show"])
    assert result.exit_code == 0
    assert "Configuration is empty" in result.output

def test_config_add_and_show_ollama(runner):
    """Test adding an ollama model and then showing the configuration."""
    # Add a model
    add_result = runner.invoke(cli, [
        "config", "add",
        "--provider", "ollama",
        "--model", "qwen3:1.7b"
    ])
    assert add_result.exit_code == 0
    assert "Successfully configured model 'qwen3:1.7b'" in add_result.output

    # Show the configuration
    show_result = runner.invoke(cli, ["config", "show"])
    assert show_result.exit_code == 0
    
    config_data = json.loads(show_result.output)
    assert "ollama" in config_data["providers"]
    assert "qwen3:1.7b" in config_data["providers"]["ollama"]["models"]
    assert config_data["providers"]["ollama"]["llm_type"] == "ollama"

def test_config_use_model(runner):
    """Test `modelforge config use` command."""
    # First, add a model to use
    runner.invoke(cli, [
        "config", "add",
        "--provider", "test_provider",
        "--model", "test_model"
    ])

    # Now, use the model
    use_result = runner.invoke(cli, [
        "config", "use",
        "--provider", "test_provider",
        "--model", "test_model"
    ])
    assert use_result.exit_code == 0
    assert "Successfully set 'test_model'" in use_result.output

    # Verify the current model is set
    current_model = config.get_current_model()
    assert current_model["provider"] == "test_provider"
    assert current_model["model"] == "test_model"

def test_config_remove_model(runner):
    """Test `modelforge config remove` command."""
    # Add a model to remove
    runner.invoke(cli, [
        "config", "add",
        "--provider", "ollama",
        "--model", "qwen3:1.7b"
    ])

    # Remove the model
    remove_result = runner.invoke(cli, [
        "config", "remove",
        "--provider", "ollama",
        "--model", "qwen3:1.7b"
    ])
    assert remove_result.exit_code == 0
    assert "Removed provider 'ollama' (no models remaining)." in remove_result.output

    # Verify the model is gone
    show_result = runner.invoke(cli, ["config", "show"])
    assert "qwen3:1.7b" not in show_result.output 