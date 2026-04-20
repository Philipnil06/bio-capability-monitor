"""Common provider interface."""

from __future__ import annotations

from abc import ABC, abstractmethod

from ..types import BuilderRunResult, MonitorResult, TaskSpec


class ModelProvider(ABC):
    """Small chat-provider interface used by builder and monitor."""

    @abstractmethod
    def generate_builder_response(self, task: TaskSpec, system_prompt: str) -> str:
        """Generate a builder JSON response."""

    @abstractmethod
    def generate_monitor_response(
        self,
        task: TaskSpec,
        builder_result: BuilderRunResult,
        system_prompt: str,
    ) -> str:
        """Generate a monitor JSON response."""

