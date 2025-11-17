from datetime import datetime
from enum import Enum
from typing import Annotated

from pydantic import BaseModel, Field, StringConstraints


class ArxivPaper(BaseModel):
    arxiv: Annotated[str, StringConstraints(min_length=1)]
    title: Annotated[str, StringConstraints(min_length=1)]
    abstract: Annotated[str, StringConstraints(min_length=1)]
    published_on: datetime
    categories: list[str] = Field(default_factory=list)


class PaperSource(str, Enum):
    ALPHAXIV = "alphaxiv"
    HUGGINGFACE = "hf"
    BOTH = "both"


class BasePaper(BaseModel):
    arxiv_id: Annotated[str, StringConstraints(min_length=1)]
    title: Annotated[str, StringConstraints(min_length=1)]
    abstract: Annotated[str, StringConstraints(min_length=1)]
    published_on: Annotated[str, StringConstraints(min_length=1)]


class RawPaper(BasePaper):
    votes: int | None = None


class RankedPaper(BasePaper):
    score: int = Field(ge=1, le=2)
    alphaxiv_rank: int | None = None
    hf_rank: int | None = None
    source: PaperSource

    @property
    def average_rank(self) -> float:
        ranks = [r for r in [self.alphaxiv_rank, self.hf_rank] if r is not None]
        return sum(ranks) / len(ranks) if ranks else float("inf")

    def sort_key(self) -> tuple[int, float]:
        return (-self.score, self.average_rank)
