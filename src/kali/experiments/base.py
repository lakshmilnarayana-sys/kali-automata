"""Abstract base for all fault injectors."""

from __future__ import annotations

import abc
from typing import Any, Dict

from kali.models.experiment import ActionResult


class FaultInjector(abc.ABC):
    """Base class all fault injectors must implement."""

    name: str

    @abc.abstractmethod
    async def inject(self, provider: Dict[str, Any], duration: int, dry_run: bool = False) -> ActionResult:
        """Inject the fault and hold it for `duration` seconds."""

    @abc.abstractmethod
    async def rollback(self, provider: Dict[str, Any], dry_run: bool = False) -> ActionResult:
        """Undo any fault side effects."""
