"""Minimal OpenRouter client. Reads OPENROUTER_API_KEY from .env."""

import os
import sys

from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

DEFAULT_MODEL = os.getenv("OPENROUTER_MODEL", "anthropic/claude-sonnet-5.5")


def get_client() -> OpenAI:
    key = os.getenv("OPENROUTER_API_KEY")
    if not key:
        sys.exit("OPENROUTER_API_KEY is missing. Paste your key into .env after the '='.")
    return OpenAI(base_url="https://openrouter.ai/api/v1", api_key=key)


def ask(prompt: str, model: str = DEFAULT_MODEL, system: str = None, max_tokens: int = 1024) -> str:
    messages = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": prompt})
    response = get_client().chat.completions.create(
        model=model, messages=messages, max_tokens=max_tokens
    )
    return response.choices[0].message.content


if __name__ == "__main__":
    prompt = " ".join(sys.argv[1:]) or "Reply with exactly: OpenRouter is connected."
    print(ask(prompt))
