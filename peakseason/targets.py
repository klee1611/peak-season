"""Load and validate seasonal target definitions (targets/*.yaml).

Everything that differs between maples, cherry blossoms, etc. lives in the YAML
and prompt files; the code below knows nothing about any specific plant.
"""

from pathlib import Path

import yaml
from pydantic import BaseModel, Field, model_validator


class Stage(BaseModel):
    id: str
    label: str
    go_now: bool = False


class Taxon(BaseModel):
    name: str
    rank: str


class Annotation(BaseModel):
    """iNaturalist controlled term used as a free signal (labels, resolved to IDs at runtime)."""

    term: str
    in_season: list[str]  # values that mark the target as in season in a cell
    # value label -> stage ids it is compatible with; used only by validate.py
    validation_groups: dict[str, list[str]] = Field(default_factory=dict)


class Target(BaseModel):
    id: str
    display_name: str
    local_names: dict[str, str] = Field(default_factory=dict)
    inat_taxa: list[Taxon]
    stages: list[Stage]
    photo_prompt: str
    text_prompt: str
    search_queries: dict[str, str] = Field(default_factory=dict)
    inat_annotation: Annotation | None = None
    validated: bool = False  # flipped by hand once validate.py passes (see NOTES.md)

    @model_validator(mode="after")
    def _check(self) -> "Target":
        ids = [s.id for s in self.stages]
        if len(ids) < 2:
            raise ValueError(f"{self.id}: needs at least two stages")
        if len(set(ids)) != len(ids):
            raise ValueError(f"{self.id}: duplicate stage ids")
        if not any(s.go_now for s in self.stages):
            raise ValueError(f"{self.id}: at least one stage must be go_now")
        if not self.inat_taxa:
            raise ValueError(f"{self.id}: inat_taxa is empty")
        if self.inat_annotation:
            for value, stages in self.inat_annotation.validation_groups.items():
                unknown = set(stages) - set(ids)
                if unknown:
                    raise ValueError(f"{self.id}: annotation group {value!r} has {unknown}")
        return self

    @property
    def stage_ids(self) -> list[str]:
        return [s.id for s in self.stages]

    def stage_index(self, stage_id: str) -> int:
        return self.stage_ids.index(stage_id)

    def is_go_now(self, stage_id: str) -> bool:
        return any(s.id == stage_id and s.go_now for s in self.stages)


def load_target(path: Path, root: Path | None = None) -> Target:
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    target = Target.model_validate(data)
    base = root or path.parent.parent
    for prompt in (target.photo_prompt, target.text_prompt):
        if not (base / prompt).is_file():
            raise ValueError(f"{target.id}: prompt file not found: {prompt}")
    return target


def load_targets(targets_dir: Path) -> list[Target]:
    targets = [load_target(p) for p in sorted(targets_dir.glob("*.yaml"))]
    ids = [t.id for t in targets]
    if len(set(ids)) != len(ids):
        raise ValueError("duplicate target ids")
    return targets
