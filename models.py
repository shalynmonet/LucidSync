"""Pydantic models for LucidSync dream capture and scene structure."""

from pydantic import BaseModel, ConfigDict, Field, model_validator


class DreamCharacter(BaseModel):
    """A person or creature identified in one or more dream scenes."""

    model_config = ConfigDict(extra="forbid")

    id: str
    name: str
    visual_description: str


class DreamObject(BaseModel):
    """An object that may later be grounded to pixels in a scene image."""

    model_config = ConfigDict(extra="forbid")

    id: str
    name: str
    visual_description: str


class DreamScene(BaseModel):
    """One scene, kept in the order it appeared in the dream report."""

    model_config = ConfigDict(extra="forbid")

    scene_number: int
    setting: str
    characters: list[DreamCharacter]
    objects: list[DreamObject]
    actions: list[str]
    emotions: list[str]
    colors: list[str]
    vividness: int = Field(ge=1, le=5)


class DreamStructure(BaseModel):
    """Model-produced portion of a DreamRecord."""

    model_config = ConfigDict(extra="forbid")

    scenes: list[DreamScene]

    @model_validator(mode="after")
    def validate_scene_order_and_character_identity(self) -> "DreamStructure":
        if not self.scenes:
            raise ValueError("A dream record must contain at least one scene.")
        expected_numbers = list(range(1, len(self.scenes) + 1))
        actual_numbers = [scene.scene_number for scene in self.scenes]
        if actual_numbers != expected_numbers:
            raise ValueError("Scene numbers must follow story order, starting at 1.")

        character_details: dict[str, tuple[str, str]] = {}
        for scene in self.scenes:
            seen_ids: set[str] = set()
            for character in scene.characters:
                if character.id in seen_ids:
                    raise ValueError(
                        f"Character id {character.id!r} appears twice in scene "
                        f"{scene.scene_number}."
                    )
                seen_ids.add(character.id)

                details = (character.name, character.visual_description)
                previous = character_details.get(character.id)
                if previous is not None and previous != details:
                    raise ValueError(
                        f"Character id {character.id!r} has inconsistent details "
                        "across scenes."
                    )
                character_details[character.id] = details
        return self


class DreamRecord(BaseModel):
    """A captured dream report plus its validated scene structure."""

    model_config = ConfigDict(extra="forbid")

    dream_report: str
    mood_on_waking: str
    vividness: int = Field(ge=1, le=5)
    scenes: list[DreamScene]

    @model_validator(mode="after")
    def validate_scene_order_and_character_identity(self) -> "DreamRecord":
        DreamStructure(scenes=self.scenes)
        return self
