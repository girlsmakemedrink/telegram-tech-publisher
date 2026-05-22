"""Source interface and Candidate shape."""

from datetime import datetime
from typing import Protocol

from pydantic import BaseModel, HttpUrl


class Candidate(BaseModel):
    source: str
    external_id: str
    title: str
    body: str
    url: HttpUrl
    published_at: datetime


class Source(Protocol):
    name: str

    async def poll(self) -> list[Candidate]: ...
