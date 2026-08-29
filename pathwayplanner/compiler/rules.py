"""Rule-based action compiler (Phase II baseline).

Transparent by construction: an ordered list of (predicate, chooser)
rules, falling back to the action's own first proposal. Adaptive /
learned selection replaces the chooser later without changing callers.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Callable

from pathwayplanner.compiler.base import Compiler, Implementation
from pathwayplanner.states import State

if TYPE_CHECKING:
    from pathwayplanner.actions.base import Action

Rule = tuple[
    Callable[[State, "Action"], bool],
    Callable[[State, "Action"], Implementation],
]


@dataclass
class RuleBasedCompiler(Compiler):
    """First matching rule wins; otherwise the action's first proposal."""

    rules: list[Rule] = field(default_factory=list)

    def add_rule(
        self,
        predicate: Callable[[State, Action], bool],
        chooser: Callable[[State, Action], Implementation],
    ) -> None:
        self.rules.append((predicate, chooser))

    def compile(self, state: State, action: "Action") -> Implementation:
        for predicate, chooser in self.rules:
            if predicate(state, action):
                return chooser(state, action)
        proposals = action.propose(state)
        if not proposals:
            raise ValueError(f"action {action.name!r} proposed no implementations")
        return proposals[0]
