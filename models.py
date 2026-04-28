from dataclasses import field

from pydantic import BaseModel


class LedCommand(BaseModel):
    color: tuple[int, int, int]
    timings: list[float] = field(default_factory=list)
    off_color: tuple[int, int, int] = field(default=(0, 0, 0))
