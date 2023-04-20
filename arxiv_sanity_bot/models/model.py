from typing import Protocol


class LLM(Protocol):

    def summarize_abstract(self, abstract: str) -> str:  # pragma: no cover
        pass

    def generate_bot_summary(self, n_papers_considered: int, n_papers_reported: int):
        pass
