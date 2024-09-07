from __future__ import annotations

from pydantic import ConfigDict, Extra, constr


def dt_config(title: str | None = None) -> ConfigDict:
    return ConfigDict(
        title=title,
        extra=Extra.forbid,
        frozen=True,
        validate_default=True,
        validate_assignment=True,
    )


NonEmptyStr = constr(min_length=1)
