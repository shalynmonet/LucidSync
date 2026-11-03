"""Local storyboard and image revision metadata."""

from pydantic import BaseModel, ConfigDict, Field


class ImageRevision(BaseModel):
    model_config = ConfigDict(extra="forbid")
    round_number: int = Field(ge=0)
    image_path: str | None = None
    response_id: str | None = None
    instruction: str = "Initial render"


class StoryboardFrame(BaseModel):
    model_config = ConfigDict(extra="forbid")
    scene_number: int = Field(ge=1)
    prompt: str
    revisions: list[ImageRevision]
    locked: bool = False


class Storyboard(BaseModel):
    model_config = ConfigDict(extra="forbid")
    frames: list[StoryboardFrame]
