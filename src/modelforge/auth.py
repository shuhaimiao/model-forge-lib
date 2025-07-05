from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
import getpass
import keyring
import time
import requests

class AuthStrategy(ABC):
    """Abstract base class for all authentication strategies."""

    @abstractmethod
    def authenticate(self) -> Dict[str, Any]:
        """
        Perform the authentication flow.

        Returns:
            A dictionary containing the necessary credentials (e.g., api_key, token).
        """
        pass

    @abstractmethod
    def get_credentials(self) -> Optional[Dict[str, Any]]:
        """
        Retrieve stored credentials without performing a new authentication.

        Returns:
            A dictionary of stored credentials or None if not found.
        """
        pass

class ApiKeyAuth(AuthStrategy):
    """Handles simple API key authentication using the system's keyring."""

    def __init__(self, provider_name: str):
        """
        Initializes the strategy for a specific provider.

        Args:
            provider_name: The unique name of the provider (e.g., 'openai').
                           This is used as the service name in the keyring.
        """
        self.provider_name = provider_name
        self.username = f"{provider_name}_user"  # A consistent username for the keyring entry

    def authenticate(self) -> Dict[str, Any]:
        """
        Prompts the user for an API key and saves it to the keyring.
        """
        print(f"Please enter the API key for {self.provider_name}:")
        api_key = getpass.getpass("API Key: ")

        if not api_key:
            raise ValueError("API key cannot be empty.")

        keyring.set_password(self.provider_name, self.username, api_key)
        print(f"API key for {self.provider_name} has been stored securely.")
        return {"api_key": api_key}

    def get_credentials(self) -> Optional[Dict[str, Any]]:
        """
        Retrieves the API key from the keyring.
        """
        api_key = keyring.get_password(self.provider_name, self.username)
        if api_key:
            return {"api_key": api_key}
        return None

class DeviceFlowAuth(AuthStrategy):
    """Handles the OAuth 2.0 Device Authorization Grant flow."""

    def __init__(self, provider_name: str, client_id: str, device_code_url: str, token_url: str, scope: str):
        self.provider_name = provider_name
        self.client_id = client_id
        self.device_code_url = device_code_url
        self.token_url = token_url
        self.scope = scope
        self.username = f"{provider_name}_user"

    def authenticate(self) -> Dict[str, Any]:
        """Performs the full device auth flow and stores the token."""
        # Step 1: Get the device and user codes
        response = requests.post(self.device_code_url, data={"client_id": self.client_id, "scope": self.scope})
        response.raise_for_status()
        device_code_data = response.json()

        print("\n--- Device Authentication ---")
        print(f"Please open the following URL in your browser: {device_code_data['verification_uri']}")
        print(f"And enter this code: {device_code_data['user_code']}")
        print("---------------------------\n")

        # Step 2: Poll for the access token
        while True:
            time.sleep(device_code_data['interval'])
            token_response = requests.post(self.token_url, data={
                "client_id": self.client_id,
                "device_code": device_code_data['device_code'],
                "grant_type": "urn:ietf:params:oauth:grant-type:device_code"
            })
            token_data = token_response.json()
            if "access_token" in token_data:
                access_token = token_data["access_token"]
                keyring.set_password(self.provider_name, self.username, access_token)
                print(f"Successfully authenticated and stored token for {self.provider_name}.")
                return {"access_token": access_token}
            elif token_data.get("error") == "authorization_pending":
                continue
            else:
                raise Exception(f"Failed to get access token: {token_data.get('error_description')}")

    def get_credentials(self) -> Optional[Dict[str, Any]]:
        """Retrieves the stored access token from the keyring."""
        access_token = keyring.get_password(self.provider_name, self.username)
        if access_token:
            return {"access_token": access_token}
        return None

class LocalAuth(AuthStrategy):
    """Handles local models like Ollama that require no authentication."""

    def authenticate(self) -> Dict[str, Any]:
        """Local models do not require authentication."""
        print("Local model selected. No authentication is required.")
        return {}

    def get_credentials(self) -> Optional[Dict[str, Any]]:
        """Local models do not have stored credentials."""
        return {}

# We will later implement concrete strategies that inherit from this base class:
#
# class DeviceFlowAuth(AuthStrategy):
#     """Handles the OAuth 2.0 Device Authorization Grant flow."""
#     ...
#
# class LocalAuth(AuthStrategy):
#     """Handles connection to local models like Ollama that require no auth."""
#     ... 