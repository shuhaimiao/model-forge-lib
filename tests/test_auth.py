import pytest
from unittest.mock import MagicMock
from modelforge.auth import ApiKeyAuth, get_credentials
from modelforge.auth import DeviceFlowAuth
from datetime import datetime, timedelta
import json

@pytest.fixture
def mock_keyring(mocker):
    """Mocks the keyring module."""
    return mocker.patch('modelforge.auth.keyring', autospec=True)

@pytest.fixture
def mock_getpass(mocker):
    """Mocks the getpass.getpass function."""
    return mocker.patch('modelforge.auth.getpass.getpass', return_value="test-api-key")

@pytest.fixture
def mock_requests(mocker):
    """Mocks the requests module."""
    return mocker.patch('modelforge.auth.requests', autospec=True)

def test_api_key_auth_authenticate(mock_keyring, mock_getpass):
    """Test that ApiKeyAuth prompts for a key and saves it."""
    auth_strategy = ApiKeyAuth("test_provider")
    credentials = auth_strategy.authenticate()

    mock_getpass.assert_called_once()
    mock_keyring.set_password.assert_called_once_with("test_provider", "test_provider_user", "test-api-key")
    assert credentials == {"api_key": "test-api-key"}

def test_api_key_auth_get_credentials_found(mock_keyring):
    """Test retrieving a stored API key."""
    mock_keyring.get_password.return_value = "stored-api-key"
    
    auth_strategy = ApiKeyAuth("test_provider")
    credentials = auth_strategy.get_credentials()

    mock_keyring.get_password.assert_called_once_with("test_provider", "test_provider_user")
    assert credentials == {"api_key": "stored-api-key"}

def test_api_key_auth_get_credentials_not_found(mock_keyring):
    """Test retrieving a non-existent API key."""
    mock_keyring.get_password.return_value = None
    
    auth_strategy = ApiKeyAuth("test_provider")
    credentials = auth_strategy.get_credentials()

    assert credentials is None

def test_device_flow_auth_success(mock_keyring, mock_requests):
    """Test the successful device flow authentication."""
    # Arrange
    mock_requests.post.side_effect = [
        # First call to get device code
        MagicMock(
            status_code=200,
            json=lambda: {
                "device_code": "test_device_code",
                "user_code": "ABCD-1234",
                "verification_uri": "https://test.com/activate",
                "interval": 1
            }
        ),
        # Second call, pending
        MagicMock(
            status_code=200,
            json=lambda: {"error": "authorization_pending"}
        ),
        # Third call, success
        MagicMock(
            status_code=200,
            json=lambda: {
                "access_token": "test-access-token",
                "token_type": "bearer",
                "expires_in": 3600
            }
        )
    ]

    auth_strategy = DeviceFlowAuth(
        provider_name="github",
        client_id="test_client_id",
        device_code_url="https://test.com/device/code",
        token_url="https://test.com/login/oauth/access_token",
        scope="read:user"
    )

    # Act
    credentials = auth_strategy.authenticate()

    # Assert
    assert mock_requests.post.call_count == 3
    mock_keyring.set_password.assert_called_once()
    assert credentials == {"access_token": "test-access-token"}

def test_device_flow_get_credentials_valid_token(mock_keyring):
    """Test retrieving a valid, non-expired device flow token."""
    # Arrange
    now = datetime.now()
    token_info = {
        "access_token": "valid-token",
        "acquired_at": now.isoformat(),
        "expires_in": 3600 # 1 hour
    }
    mock_keyring.get_password.return_value = json.dumps(token_info)
    auth_strategy = DeviceFlowAuth("github", "", "", "", "")

    # Act
    credentials = auth_strategy.get_credentials()

    # Assert
    assert credentials == {"access_token": "valid-token"}

def test_device_flow_get_credentials_expired_token(mock_keyring):
    """Test that an expired token is not returned."""
    # Arrange
    yesterday = datetime.now() - timedelta(days=1)
    token_info = {
        "access_token": "expired-token",
        "acquired_at": yesterday.isoformat(),
        "expires_in": 3600 # Expired long ago
    }
    mock_keyring.get_password.return_value = json.dumps(token_info)
    auth_strategy = DeviceFlowAuth("github", "", "", "", "")

    # Act
    credentials = auth_strategy.get_credentials()

    # Assert
    assert credentials is None 