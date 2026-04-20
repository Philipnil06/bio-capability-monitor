"""OpenAI-compatible local endpoint provider hook."""

from __future__ import annotations

import os

from .openai_provider import OpenAIProvider


class OpenAICompatibleProvider(OpenAIProvider):
    """OpenAI SDK provider configured with a custom base URL."""

    def __init__(
        self,
        builder_model: str,
        monitor_model: str,
        base_url: str,
        api_key: str | None = None,
    ) -> None:
        super().__init__(builder_model, monitor_model, api_key or os.environ.get("OPENAI_COMPATIBLE_API_KEY") or "local")
        self.base_url = base_url

    def _client_or_error(self):
        try:
            from openai import OpenAI
        except ImportError as exc:
            raise RuntimeError(
                "The openai package is required for provider=openai_compatible. Run pip install -r requirements.txt."
            ) from exc
        if self._client is None:
            self._client = OpenAI(api_key=self.api_key, base_url=self.base_url)
        return self._client
