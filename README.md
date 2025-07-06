# Model Forge Library

A reusable library for managing LLM providers, authentication, and model selection.

This library is intended to be used by various Python-based AI projects to provide a consistent way to handle LLM interactions.

## High-Level Design

The library is composed of three core modules:

-   **`config`**: Manages the central configuration file (`~/.config/modelforge/models.json`) where all provider and model settings are stored.
-   **`auth`**: Provides a suite of authentication strategies (API Key, OAuth 2.0 Device Flow, and a No-Op for local models) and handles secure credential storage using the system's native keyring.
-   **`registry`**: Acts as the main entry point and factory. It reads the configuration, invokes the appropriate authentication strategy, and instantiates ready-to-use, LangChain-compatible LLM objects.

## Local Development & Testing

To test the library locally, you can use the built-in Command-Line Interface (CLI).

1.  **Set up a virtual environment:**
    ```bash
    python -m venv venv
    source venv/bin/activate
    ```

2.  **Install the library in editable mode:**
    This allows you to use the CLI and reflects any code changes immediately without reinstalling.
    ```bash
    pip install -e .
    ```

3.  **Use the CLI to manage your models:**
    ```bash
    # Show the current configuration
    modelforge config show

    # Add a local Ollama model
    modelforge config add --provider ollama --model qwen3:1.7b

    # Add OpenAI models with API key
    modelforge config add --provider openai --model gpt-4o-mini --api-key "YOUR_API_KEY_HERE"
    modelforge config add --provider openai --model gpt-4o --api-model-name "gpt-4o" --api-key "YOUR_API_KEY_HERE"

    # Add a provider requiring an API key (Google Gemini)
    modelforge config add --provider google --model gemini-pro --api-model-name "gemini-1.5-pro" --api-key "YOUR_API_KEY_HERE"

    # Add GitHub Copilot and trigger the device authentication flow
    modelforge config add --provider github_copilot --model claude-3.7-sonnet --dev-auth

    # Set a model to be the default
    modelforge config use --provider ollama --model qwen3:1.7b
    ```

## Integration Guide

To use this library in a host application (e.g., RAG-Forge):

1.  **Install the library:**
    ```bash
    # For development, install from a local path
    pip install -e /path/to/model-forge-lib

    # In the future, you would install from a package registry like PyPI
    # pip install model-forge-lib
    ```

2.  **Use the `ModelRegistry` in your application:**
    ```python
    from modelforge.registry import ModelRegistry

    # 1. Initialize the registry
    registry = ModelRegistry()

    # 2. See which models the user has configured
    available_models = registry.list_models()
    print(f"Available models: {available_models}")
    # Example output: ['ollama/qwen3:1.7b', 'github_copilot/claude-3.7-sonnet']

    # 3. Get a fully authenticated model instance
    if available_models:
        model_id = available_models[0]
        llm = registry.get_model_instance(model_id)

        if llm:
            # Now you have a LangChain-compatible LLM object to use
            response = llm.invoke("Tell me a joke.")
            print(response)
    ```

## Features

- **Multi-Provider Support**: OpenAI, Ollama, GitHub Copilot, Google Gemini
- **Flexible Authentication**: API Key, OAuth 2.0 Device Flow, Local (no auth)
- **Secure Credential Storage**: Uses system keyring for API keys and tokens
- **LangChain Integration**: Provides ready-to-use LangChain-compatible model instances
- **Centralized Configuration**: Single configuration file managing all providers and models
