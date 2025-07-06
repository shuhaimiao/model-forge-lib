from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
import getpass
import keyring
import time
import requests
import json
from datetime import datetime, timedelta

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
        headers = {"Accept": "application/json"}
        payload = {"client_id": self.client_id, "scope": self.scope}
        response = requests.post(self.device_code_url, data=payload, headers=headers)
        
        try:
            response.raise_for_status()
            device_code_data = response.json()
        except (requests.exceptions.HTTPError, requests.exceptions.JSONDecodeError) as e:
            print(f"Error requesting device code: {e}")
            print(f"Response text: {response.text}")
            raise

        print("\n--- Device Authentication ---")
        print(f"Please open the following URL in your browser: {device_code_data['verification_uri']}")
        print(f"And enter this code: {device_code_data['user_code']}")
        print("---------------------------\n")

        # Step 2: Poll for the access token
        while True:
            time.sleep(device_code_data['interval'])
            token_payload = {
                "client_id": self.client_id,
                "device_code": device_code_data['device_code'],
                "grant_type": "urn:ietf:params:oauth:grant-type:device_code"
            }
            token_response = requests.post(self.token_url, data=token_payload, headers=headers)
            
            try:
                token_data = token_response.json()
                token_response.raise_for_status()
            except (requests.exceptions.HTTPError, requests.exceptions.JSONDecodeError) as e:
                # This part is different from the original script, but good for debug
                if "error" in token_response.text:
                     error_info = token_response.json()
                     if error_info.get("error") == "authorization_pending":
                         continue
                     elif error_info.get("error") == "slow_down":
                         # The interval is in the response, but we can just add 5 as a fallback
                         time.sleep(5)
                         continue
                
                print(f"Error polling for token: {e}")
                print(f"Response text: {token_response.text}")
                raise

            if "access_token" in token_data:
                # Store the complete token information including expiration
                token_info = {
                    "access_token": token_data["access_token"],
                    "token_type": token_data.get("token_type", "bearer"),
                    "expires_in": token_data.get("expires_in", 28800),  # Default to 8 hours
                    "acquired_at": datetime.now().isoformat(),
                    "scope": token_data.get("scope", self.scope)
                }
                
                # Store refresh token if provided
                if "refresh_token" in token_data:
                    token_info["refresh_token"] = token_data["refresh_token"]
                
                # Store as JSON string in keyring
                keyring.set_password(self.provider_name, self.username, json.dumps(token_info))
                print(f"Successfully authenticated and stored token for {self.provider_name}.")
                return {"access_token": token_data["access_token"]}
            elif token_data.get("error") == "authorization_pending":
                continue
            elif token_data.get("error") == "slow_down":
                time.sleep(5)
                continue
            else:
                raise Exception(f"Failed to get access token: {token_data.get('error_description')}")

    def get_credentials(self) -> Optional[Dict[str, Any]]:
        """Retrieves the stored access token from the keyring, checking for expiration."""
        stored_data = keyring.get_password(self.provider_name, self.username)
        if not stored_data:
            return None
        
        try:
            # Try to parse as JSON (new format)
            token_info = json.loads(stored_data)
            
            # Check if token is expired
            acquired_at = datetime.fromisoformat(token_info["acquired_at"])
            expires_in = token_info.get("expires_in", 28800)  # Default 8 hours
            expiry_time = acquired_at + timedelta(seconds=expires_in)
            
            # Add 5-minute buffer before expiration
            buffer_time = expiry_time - timedelta(minutes=5)
            
            if datetime.now() >= buffer_time:
                print(f"Token for {self.provider_name} is expired or expiring soon. Please re-authenticate.")
                print(f"Run: modelforge config add --provider {self.provider_name} --model <model> --dev-auth")
                return None
            
            return {"access_token": token_info["access_token"]}
            
        except (json.JSONDecodeError, KeyError, ValueError):
            # Handle legacy format (just the token string)
            # This is for backward compatibility
            if stored_data.startswith('gho_') or stored_data.startswith('ghr_'):
                print(f"Warning: Legacy token format detected for {self.provider_name}. Consider re-authenticating for better expiration handling.")
                return {"access_token": stored_data}
            return None

    def get_token_info(self) -> Optional[Dict[str, Any]]:
        """Get detailed token information for debugging purposes."""
        stored_data = keyring.get_password(self.provider_name, self.username)
        if not stored_data:
            return None
        
        try:
            token_info = json.loads(stored_data)
            acquired_at = datetime.fromisoformat(token_info["acquired_at"])
            expires_in = token_info.get("expires_in", 28800)
            expiry_time = acquired_at + timedelta(seconds=expires_in)
            
            return {
                "acquired_at": acquired_at,
                "expires_in": expires_in,
                "expiry_time": expiry_time,
                "time_remaining": expiry_time - datetime.now(),
                "is_expired": datetime.now() >= expiry_time,
                "token_preview": token_info["access_token"][-10:] if token_info.get("access_token") else "N/A"
            }
        except (json.JSONDecodeError, KeyError, ValueError):
            return {"legacy_format": True, "token_preview": stored_data[-10:] if stored_data else "N/A"}

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

# A mapping from auth_strategy names in the config to the classes that handle them.
AUTH_STRATEGY_MAP = {
    "api_key": ApiKeyAuth,
    "device_flow": DeviceFlowAuth,
    "local": LocalAuth,
}

def get_credentials(provider_name: str, model_alias: str, verbose: bool = False) -> Optional[Dict[str, Any]]:
    """
    A factory function that retrieves stored credentials for a given provider.
    
    It reads the main config, determines the correct auth strategy,
    instantiates the handler, and returns the credentials.

    Args:
        provider_name: The name of the provider.
        model_alias: The alias of the model (not directly used here but good for context).
        verbose: If True, print debug information.

    Returns:
        A dictionary of credentials, or None if not found or on error.
    """
    from . import config as app_config  # Use a different name to avoid confusion
    
    full_config, _ = app_config.get_config()
    provider_data = full_config.get("providers", {}).get(provider_name)

    if not provider_data:
        print(f"Error: Could not find provider '{provider_name}' in config for auth.")
        return None

    auth_strategy_name = provider_data.get("auth_strategy")
    auth_class = AUTH_STRATEGY_MAP.get(auth_strategy_name)
    
    if verbose:
        print(f"🔍 DEBUG - Getting credentials:")
        print(f"   Provider: {provider_name}")
        print(f"   Model: {model_alias}")
        print(f"   Auth strategy: {auth_strategy_name}")

    if not auth_class:
        print(f"Error: Unknown auth_strategy '{auth_strategy_name}' for provider '{provider_name}'.")
        return None

    # Instantiate the auth strategy class
    if auth_strategy_name == "device_flow":
        auth_details = provider_data.get("auth_details", {})
        if verbose:
            print(f"   Device flow details: {auth_details}")
        auth_handler = auth_class(
            provider_name=provider_name,
            **auth_details
        )
    else:
        auth_handler = auth_class(provider_name)

    credentials = auth_handler.get_credentials()
    if verbose:
        print(f"   Retrieved credentials: {'Yes' if credentials else 'None'}")
        if credentials:
            cred_keys = list(credentials.keys())
            print(f"   Credential keys: {cred_keys}")
    
    return credentials 