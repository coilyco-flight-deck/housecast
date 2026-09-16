"""The definition set: the editable unit, and the overlay that applies it.

This is the thing a tester changes. It holds tool prose, parameter prose and
the instruction block, and it is versioned, attributable, diffable and
revertable because every one of those is a requirement the loop leans on rather
than a nicety.

`overlay` is where the whole architecture lives. It clones what `tools/list`
returned and rewrites the clone. The running subject is never mutated, so the
tool calls the model produces route back to the unedited server and the edit
cannot change what a tool *does*, only what it *says*. That is the difference
between measuring prose and measuring a fork.

A set is identified by its prose and nothing else, so an edit-and-revert
collides with its origin instead of arriving as a third version whose numbers a
reader would compare against the first two.
"""

from __future__ import annotations

import copy
import json
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from typing import Any

from housecast.digest import digest

# A warning rather than a refusal: a description long enough to bury its own
# precondition may be exactly what the tester is measuring.
LONG_DESCRIPTION = 600


class DefinitionError(ValueError):
    """Raised when a set names prose the subject does not advertise."""


@dataclass(frozen=True)
class ToolProse:
    """One tool's editable text."""

    description: str
    parameters: Mapping[str, str] = field(default_factory=dict)

    def as_dict(self) -> dict[str, Any]:
        return {"description": self.description, "parameters": dict(self.parameters)}


@dataclass(frozen=True)
class DefinitionSet:
    """One state of the prose under test, over one subject."""

    tools: Mapping[str, ToolProse]
    instructions: str = ""
    authored_by: str = "human:unknown"
    parent: str | None = None
    label: str = ""

    def __post_init__(self) -> None:
        if not self.authored_by.startswith(("human:", "model:")):
            raise DefinitionError(
                f"authored_by must be 'human:<name>' or 'model:<id>', got "
                f"{self.authored_by!r}. A loop where the subject, the editor and "
                "the grader are all models is the failure this field makes visible."
            )

    def canonical(self) -> str:
        return json.dumps(
            {
                "tools": {name: self.tools[name].as_dict() for name in sorted(self.tools)},
                "instructions": self.instructions,
            },
            ensure_ascii=False,
            sort_keys=True,
        )

    @property
    def digest(self) -> str:
        return digest(self.canonical())

    def short(self) -> str:
        return self.digest.removeprefix("sha256:")[:12]

    def overlay(self, advertised: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
        """Rewrite a clone of `tools/list` and hand that to the model.

        Order is preserved because selection depends on what else was on offer
        and where. A client that sorts this has changed the measurement.
        """
        names = {tool["name"] for tool in advertised}
        unknown = set(self.tools) - names
        if unknown:
            raise DefinitionError(
                f"this set names tools the subject does not advertise: {sorted(unknown)}. "
                "Prose is measured against the subject that was hosted, not a later one."
            )
        out: list[dict[str, Any]] = []
        for tool in advertised:
            clone = copy.deepcopy(dict(tool))
            prose = self.tools.get(clone["name"])
            if prose is not None:
                clone["description"] = prose.description
                properties = clone.get("inputSchema", {}).get("properties", {})
                for param, text in prose.parameters.items():
                    if param not in properties:
                        raise DefinitionError(
                            f"{clone['name']} has no parameter {param!r}. "
                            f"It takes: {sorted(properties)}"
                        )
                    properties[param] = dict(properties[param], description=text)
            out.append(clone)
        return out

    def diff(self, other: DefinitionSet) -> list[dict[str, str]]:
        """What changed between two sets, field by field, for the editor to show."""
        rows: list[dict[str, str]] = []
        if self.instructions != other.instructions:
            rows.append(
                {
                    "tool": "",
                    "field": "instructions",
                    "before": self.instructions,
                    "after": other.instructions,
                }
            )
        for name in sorted(set(self.tools) | set(other.tools)):
            before = self.tools.get(name)
            after = other.tools.get(name)
            if before is None or after is None:
                continue
            if before.description != after.description:
                rows.append(
                    {
                        "tool": name,
                        "field": "description",
                        "before": before.description,
                        "after": after.description,
                    }
                )
            for param in sorted(set(before.parameters) | set(after.parameters)):
                lhs = before.parameters.get(param, "")
                rhs = after.parameters.get(param, "")
                if lhs != rhs:
                    rows.append(
                        {"tool": name, "field": f"{name}.{param}", "before": lhs, "after": rhs}
                    )
        return rows

    def edited(
        self,
        *,
        tool: str,
        description: str | None = None,
        parameters: Mapping[str, str] | None = None,
        authored_by: str,
        label: str = "",
    ) -> DefinitionSet:
        """A child set with one tool's prose replaced, parented to this one."""
        if tool not in self.tools:
            raise DefinitionError(f"no tool {tool!r} in this set: {sorted(self.tools)}")
        current = self.tools[tool]
        replacement = ToolProse(
            description=current.description if description is None else description,
            parameters=dict(current.parameters) | dict(parameters or {}),
        )
        return DefinitionSet(
            tools=dict(self.tools) | {tool: replacement},
            instructions=self.instructions,
            authored_by=authored_by,
            parent=self.digest,
            label=label,
        )

    def validate(self) -> list[str]:
        """Warnings the editor shows live. Never a refusal: the tester may mean it."""
        notes: list[str] = []
        for name in sorted(self.tools):
            prose = self.tools[name]
            if not prose.description.strip():
                notes.append(f"{name}: description is empty, so the model sees only the name")
            if len(prose.description) > LONG_DESCRIPTION:
                notes.append(
                    f"{name}: description is {len(prose.description)} characters. "
                    "A precondition past 600 is one a model reads last."
                )
            for param, text in sorted(prose.parameters.items()):
                if not text.strip():
                    notes.append(f"{name}.{param}: parameter description is empty")
        return notes


def baseline_from(advertised: Sequence[Mapping[str, Any]], *, authored_by: str) -> DefinitionSet:
    """Capture exactly what the subject advertises, as the arm everything compares to.

    Taken from the live `tools/list` rather than written down beside it, so the
    baseline cannot drift from the subject it claims to describe.
    """
    tools = {
        tool["name"]: ToolProse(
            description=tool.get("description") or "",
            parameters={
                param: (spec.get("description") or "")
                for param, spec in tool.get("inputSchema", {}).get("properties", {}).items()
            },
        )
        for tool in advertised
    }
    return DefinitionSet(tools=tools, authored_by=authored_by, parent=None, label="baseline")
