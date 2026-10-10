"""The normalized Report: every source produces these, nothing downstream cares which source."""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

Source = Literal["inaturalist", "serpapi"]
Kind = Literal["photo", "text"]


class Report(BaseModel):
    source: Source
    kind: Kind
    target_id: str
    item_id: str  # stable id within the source, e.g. "inat:404999673"
    lat: float
    lng: float
    cell: str
    observed_at: datetime
    link: str
    place_guess: str | None = None

    # Photo reports
    photo_url: str | None = None  # image the model sees (displayable license only)
    license: str | None = None
    attribution: str | None = None

    # Text reports
    text: str | None = None
    title: str | None = None

    # Free signal from iNaturalist phenology annotations (labels, e.g. "Colored Leaves")
    annotations: list[str] = Field(default_factory=list)
    in_season_signal: bool = False

    # Filled in by classification / extraction
    stage: str | None = None
    confidence: float | None = None
    spot_id: str | None = None  # text reports: the famous spot they were searched for
