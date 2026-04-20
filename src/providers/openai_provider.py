"""OpenAI provider hook."""

from __future__ import annotations

import os

from .base import ModelProvider
from ..types import BuilderRunResult, TaskSpec
from ..utils import to_jsonable


class OpenAIProvider(ModelProvider):
    """Thin OpenAI chat-completions provider."""

    def __init__(self, builder_model: str, monitor_model: str, api_key: str | None = None) -> None:
        self.builder_model = builder_model
        self.monitor_model = monitor_model
        self.api_key = api_key or os.environ.get("OPENAI_API_KEY")
        self._client = None

    def _client_or_error(self):
        if not self.api_key:
            raise RuntimeError("OPENAI_API_KEY is required for provider=openai.")
        try:
            from openai import OpenAI
        except ImportError as exc:
            raise RuntimeError("The openai package is required for provider=openai. Run pip install -r requirements.txt.") from exc
        if self._client is None:
            self._client = OpenAI(api_key=self.api_key)
        return self._client

    def generate_builder_response(self, task: TaskSpec, system_prompt: str) -> str:
        client = self._client_or_error()
        response = client.chat.completions.create(
            model=self.builder_model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": str(to_jsonable(task))},
            ],
            temperature=0,
        )
        return response.choices[0].message.content or ""

    def generate_monitor_response(
        self,
        task: TaskSpec,
        builder_result: BuilderRunResult,
        system_prompt: str,
    ) -> str:
        client = self._client_or_error()
        response = client.chat.completions.create(
            model=self.monitor_model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": str({"task": to_jsonable(task), "builder_result": to_jsonable(builder_result)})},
            ],
            temperature=0,
        )
        return response.choices[0].message.content or ""

