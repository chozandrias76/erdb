from typing import List
from pydantic import Field, NonNegativeFloat, BaseModel, model_validator
from pydantic.dataclasses import dataclass
from erdb.typing.models import dt_config


@dataclass(config=dt_config())
class DamageMultiplier:
    physical: NonNegativeFloat
    magic: NonNegativeFloat
    fire: NonNegativeFloat
    lightning: NonNegativeFloat
    holy: NonNegativeFloat
    stamina: NonNegativeFloat


@dataclass(config=dt_config())
class ScalingMultiplier:
    strength: NonNegativeFloat
    dexterity: NonNegativeFloat
    intelligence: NonNegativeFloat
    faith: NonNegativeFloat
    arcane: NonNegativeFloat


@dataclass(config=dt_config())
class GuardMultiplier:
    physical: NonNegativeFloat
    magic: NonNegativeFloat
    fire: NonNegativeFloat
    lightning: NonNegativeFloat
    holy: NonNegativeFloat
    guard_boost: NonNegativeFloat


@dataclass(config=dt_config())
class ResistanceMultiplier:
    bleed: NonNegativeFloat
    frostbite: NonNegativeFloat
    poison: NonNegativeFloat
    scarlet_rot: NonNegativeFloat
    sleep: NonNegativeFloat
    madness: NonNegativeFloat
    death_blight: NonNegativeFloat


@dataclass(config=dt_config())
class ReinforcementLevel:
    level: int = Field(..., ge=0, le=25)
    damage: DamageMultiplier = Field(...)
    scaling: ScalingMultiplier = Field(...)
    guard: GuardMultiplier = Field(...)
    resistance: ResistanceMultiplier = Field(...)


class Reinforcement(BaseModel):
    reinforcements: List[ReinforcementLevel]

    @model_validator(mode="before")
    def check_list_length(cls, values):
        reinforcements = values.get("reinforcements", [])
        if not (1 <= len(reinforcements) <= 26):
            raise ValueError("Reinforcement must have between 1 and 26 items.")
        return values

    class Config:
        frozen = True  # Makes the model immutable
