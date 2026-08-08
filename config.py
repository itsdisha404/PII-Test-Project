from __future__ import annotations

import os
from dataclasses import dataclass


def _load_dotenv_if_present() -> None:
    """Minimal .env loader so this works without adding a python-dotenv
    dependency. Only sets variables that aren't already set in the real
    environment (real env vars always win)."""
    env_path = os.path.join(os.getcwd(), ".env")
    if not os.path.exists(env_path):
        return
    with open(env_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, value = line.partition("=")
            key = key.strip()
            value = value.strip().strip('"').strip("'")
            os.environ.setdefault(key, value)


_load_dotenv_if_present()


@dataclass(frozen=True)
class Settings:
    api_key: str
    base_url: str
    model: str
    app_url: str
    app_name: str

    @classmethod
    def from_env(cls) -> "Settings":
        api_key = os.environ.get("OPENROUTER_API_KEY", "")
        if not api_key:
            raise RuntimeError(
                "OPENROUTER_API_KEY is not set. Put it in your shell "
                "environment or in a local .env file (see .env.example). "
                "Never hardcode API keys in source files."
            )
        return cls(
            api_key=api_key,
            base_url=os.environ.get(
                "OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1"
            ),
            model=os.environ.get("OPENROUTER_MODEL", "openai/gpt-4o-mini"),
            app_url=os.environ.get("OPENROUTER_APP_URL", "http://localhost"),
            app_name=os.environ.get("OPENROUTER_APP_NAME", "Eligibility Chatbot"),
        )


settings = None  # lazily created via get_settings() so import never fails


def get_settings() -> Settings:
    global settings
    if settings is None:
        settings = Settings.from_env()
    return settings