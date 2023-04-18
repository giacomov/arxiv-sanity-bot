import asyncio
import re
from datetime import datetime, timedelta

import pandas as pd
import arxiv

from arxiv_sanity_bot.altmetric.scores import gather_scores
from arxiv_sanity_bot.config import (
    ARXIV_QUERY,
    ARXIV_DELAY,
    ARXIV_NUM_RETRIES,
    ARXIV_MAX_PAGES,
    ARXIV_PAGE_SIZE,
    TIMEZONE,
    WINDOW_START,
)
from arxiv_sanity_bot.events import InfoEvent
from arxiv_sanity_bot.sanitize_text import sanitize_text


def _extract_arxiv_id(entry_id):
    return re.match(".+abs/([0-9\.]+)(v[0-9]+)?", entry_id).groups()[0]


def get_all_abstracts(
    max_pages=ARXIV_MAX_PAGES,
    after=None,
    chunk_size=ARXIV_PAGE_SIZE,
) -> pd.DataFrame:

    if after is None:
        after = datetime.now(tz=TIMEZONE) - timedelta(hours=WINDOW_START)

    custom_client = arxiv.Client(
        page_size=chunk_size,
        delay_seconds=ARXIV_DELAY,
        num_retries=ARXIV_NUM_RETRIES,
    )

    rows = []

    for i, result in enumerate(
        custom_client.results(
            arxiv.Search(
                query=ARXIV_QUERY,
                max_results=chunk_size * max_pages,
                sort_by=arxiv.SortCriterion.SubmittedDate,
            )
        )
    ):
        if i > 0 and (i % chunk_size == 0):
            InfoEvent(msg=f"Fetched {i} abstracts from Arxiv")

        rows.append(
            {
                "arxiv": _extract_arxiv_id(result.entry_id),
                "title": result.title,
                "abstract": sanitize_text(result.summary),
            }
        )

        if result.published < after:
            InfoEvent(msg=f"Breaking after {i+1} papers as published date was earlier than the window start")
            break

    abstracts = pd.DataFrame(rows)

    # Fetch scores
    scores = _fetch_scores(abstracts)

    abstracts = abstracts.merge(scores, on="arxiv")

    # Filter on time
    abstracts["published_on"] = pd.to_datetime(abstracts["published_on"])

    # Filter by time window
    idx = abstracts["published_on"] > after

    return (
        abstracts[idx].sort_values(by="score", ascending=False).reset_index(drop=True)
    )


def _fetch_scores(abstracts):
    scores = pd.DataFrame(asyncio.run(gather_scores(abstracts["arxiv"].tolist())))
    return scores


def get_url(arxiv_id):

    return f"https://arxiv.org/abs/{arxiv_id}"
