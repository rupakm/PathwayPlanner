"""Name -> Action factory registry.

Same idiom as the Trails-MD spawner registry: concrete actions register
themselves under a verb name so programs and configs can refer to
actions symbolically.
"""

from __future__ import annotations

from typing import Callable

from pathwayplanner.actions.base import Action

_REGISTRY: dict[str, Callable[..., Action]] = {}


def register(name: str) -> Callable[[Callable[..., Action]], Callable[..., Action]]:
    """Class decorator registering an Action factory under `name`."""

    def deco(factory: Callable[..., Action]) -> Callable[..., Action]:
        if name in _REGISTRY:
            raise ValueError(f"action {name!r} already registered")
        _REGISTRY[name] = factory
        return factory

    return deco


def create(name: str, **kwargs) -> Action:
    """Instantiate the registered action `name`."""
    try:
        factory = _REGISTRY[name]
    except KeyError:
        raise KeyError(
            f"unknown action {name!r}; registered: {sorted(_REGISTRY)}"
        ) from None
    return factory(**kwargs)


def available() -> list[str]:
    """Registered action names."""
    return sorted(_REGISTRY)
