import pytest
from pathlib import Path

# Assuming the config module is in `modelforge.config`
# Adjust the import path if your structure is different.
from modelforge import config

# Dummy paths for testing
DUMMY_GLOBAL_CONFIG_FILE = Path("/tmp/global_config.json")
DUMMY_LOCAL_CONFIG_FILE = Path.cwd() / "model-forge" / "config.json"

@pytest.fixture(autouse=True)
def mock_config_paths(mocker):
    """
    A fixture that automatically mocks the global and local config file paths for all tests.
    This prevents tests from accidentally using or modifying the real config files.
    """
    mocker.patch.object(config, 'GLOBAL_CONFIG_FILE', DUMMY_GLOBAL_CONFIG_FILE)
    mocker.patch.object(config, 'LOCAL_CONFIG_FILE', DUMMY_LOCAL_CONFIG_FILE)
    
    # Ensure dummy files do not exist initially before each test
    if DUMMY_GLOBAL_CONFIG_FILE.exists():
        DUMMY_GLOBAL_CONFIG_FILE.unlink()
    if DUMMY_LOCAL_CONFIG_FILE.exists():
        DUMMY_LOCAL_CONFIG_FILE.unlink()
        if DUMMY_LOCAL_CONFIG_FILE.parent.exists():
            DUMMY_LOCAL_CONFIG_FILE.parent.rmdir()

    yield
    
    # Clean up dummy files after each test
    if DUMMY_GLOBAL_CONFIG_FILE.exists():
        DUMMY_GLOBAL_CONFIG_FILE.unlink()
    if DUMMY_LOCAL_CONFIG_FILE.exists():
        DUMMY_LOCAL_CONFIG_FILE.unlink()
        if DUMMY_LOCAL_CONFIG_FILE.parent.exists():
            DUMMY_LOCAL_CONFIG_FILE.parent.rmdir() 