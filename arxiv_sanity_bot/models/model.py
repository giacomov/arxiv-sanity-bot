from typing import Protocol


class LLM(Protocol):

    def summarize_abstract(self, abstract: str) -> str:  # pragma: no cover
        pass
