import pytest
from pathlib import Path

# Assuming the config module is in `modelforge.config`
# Adjust the import path if your structure is different.
from modelforge import config

# Use a dummy file path for testing
DUMMY_CONFIG_PATH = Path("/tmp/test_config.json")

@pytest.fixture(autouse=True)
def mock_config_file_for_all_tests(mocker):
    """
    A fixture that automatically mocks the config file path for all tests.
    This prevents tests from accidentally using or modifying the real config file.
    """
    mocker.patch.object(config, 'CONFIG_FILE', DUMMY_CONFIG_PATH)
    
    # Ensure the dummy file does not exist initially before each test
    if DUMMY_CONFIG_PATH.exists():
        DUMMY_CONFIG_PATH.unlink()
        
    yield
    
    # Clean up the dummy file after each test
    if DUMMY_CONFIG_PATH.exists():
        DUMMY_CONFIG_PATH.unlink() 