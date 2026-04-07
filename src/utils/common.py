# Copyright (c) MAFEvaluations project. All rights reserved.

import os

from dotenv import load_dotenv


def create_chat_client(provider: str | None = None, **kwargs):
    """Create a chat client based on the configured provider.

    Resolution order:
      1. Explicit ``provider`` argument
      2. ``EVAL_PROVIDER`` environment variable
      3. Defaults to ``"foundry"``

    Args:
        provider: ``"foundry"`` or ``"openai"``.
        **kwargs: Extra arguments forwarded to the client constructor.

    Returns:
        A configured chat client instance.
    """
    load_dotenv()
    provider = (provider or os.environ.get("EVAL_PROVIDER", "foundry")).lower()

    if provider == "foundry":
        from agent_framework.foundry import FoundryChatClient
        from azure.identity import AzureCliCredential

        return FoundryChatClient(
            project_endpoint=kwargs.pop("project_endpoint", os.environ.get("FOUNDRY_PROJECT_ENDPOINT")),
            model=kwargs.pop("model", os.environ.get("FOUNDRY_MODEL", "gpt-4o")),
            credential=kwargs.pop("credential", AzureCliCredential()),
            **kwargs,
        )

    if provider == "openai":
        from agent_framework.openai import OpenAIChatClient

        return OpenAIChatClient(
            api_key=kwargs.pop("api_key", os.environ.get("OPENAI_API_KEY")),
            model=kwargs.pop("model", os.environ.get("OPENAI_MODEL", "gpt-4o")),
            **kwargs,
        )

    raise ValueError(f"Unknown provider: {provider!r}. Use 'foundry' or 'openai'.")
