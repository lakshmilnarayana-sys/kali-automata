"""Circuit breaker — auto-aborts an experiment when health degrades too fast."""

from __future__ import annotations

import asyncio
from typing import Callable, Coroutine, List, Optional

from kali.models.experiment import CircuitBreakerConfig, Probe, ProbeResult
from kali.hypothesis.probes import run_probe


class CircuitBreakerTripped(Exception):
    def __init__(self, failures: int, reason: str) -> None:
        self.failures = failures
        self.reason = reason
        super().__init__(f"Circuit breaker tripped after {failures} failures: {reason}")


class CircuitBreaker:
    def __init__(self, config: CircuitBreakerConfig, probes: List[Probe]) -> None:
        self._config = config
        self._probes = probes
        self._failures = 0
        self._task: Optional[asyncio.Task] = None  # type: ignore[type-arg]

    async def start(self) -> None:
        if not self._config.enabled:
            return
        self._task = asyncio.create_task(self._monitor())

    async def stop(self) -> None:
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass

    async def _monitor(self) -> None:
        while True:
            await asyncio.sleep(self._config.check_interval)
            results: List[ProbeResult] = []
            for probe in self._probes:
                results.append(await run_probe(probe))

            failed = [r for r in results if not r.passed]
            if failed:
                self._failures += 1
                if self._failures >= self._config.max_failures:
                    raise CircuitBreakerTripped(
                        self._failures,
                        "; ".join(r.error or r.probe_name for r in failed),
                    )
            else:
                self._failures = 0
