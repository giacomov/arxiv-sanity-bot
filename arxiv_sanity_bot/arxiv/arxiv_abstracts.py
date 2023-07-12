import asyncio
import re
import requests
import time

import pandas as pd
import arxiv
from arxiv import SortOrder
import atoma

from arxiv_sanity_bot.altmetric.scores import gather_scores
from arxiv_sanity_bot.config import (
    ARXIV_QUERY,
    ARXIV_DELAY,
    ARXIV_NUM_RETRIES,
    ARXIV_MAX_PAGES,
    ARXIV_PAGE_SIZE,
)
from arxiv_sanity_bot.events import InfoEvent, RetryableErrorEvent, FatalErrorEvent
from arxiv_sanity_bot.sanitize_text import sanitize_text


def _extract_arxiv_id(entry_id):
    return re.match(".+abs/([0-9\.]+)(v[0-9]+)?", entry_id).groups()[0]


def get_all_abstracts(
    after,
    before,
    max_pages=ARXIV_MAX_PAGES,
    chunk_size=ARXIV_PAGE_SIZE,
) -> pd.DataFrame:

    rows = _fetch_from_arxiv_2(after, chunk_size, max_pages)

    InfoEvent(msg=f"Fetched {len(rows)} abstracts from Arxiv")

    if len(rows) == 0:
        return pd.DataFrame()

    abstracts = pd.DataFrame(rows)

    # Filter on time
    abstracts["published_on"] = pd.to_datetime(abstracts["published_on"])
    idx = (abstracts["published_on"] < before) & (abstracts["published_on"] > after)
    abstracts = abstracts[idx].reset_index(drop=True)

    if abstracts.shape[0] > 0:
        # Fetch scores
        scores = _fetch_scores(abstracts)

        abstracts = abstracts.merge(scores, on="arxiv")

        return abstracts.sort_values(by="score", ascending=False).reset_index(drop=True)

    else:
        return abstracts


def _fetch_from_arxiv(after, chunk_size, max_pages):

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
                    sort_order=SortOrder.Descending,
                )
            )
    ):
        if result.published < after:
            InfoEvent(
                msg=f"Breaking after {i} papers as published date was earlier than the window start"
            )
            break

        rows.append(
            {
                "arxiv": _extract_arxiv_id(result.entry_id),
                "title": result.title,
                "abstract": sanitize_text(result.summary),
                "published_on": result.published,
            }
        )
    return rows


def _fetch_scores(abstracts):
    scores = pd.DataFrame(asyncio.run(gather_scores(abstracts["arxiv"].tolist())))
    return scores


def get_url(arxiv_id):
    return f"https://arxiv.org/abs/{arxiv_id}"


def _fetch_from_arxiv_2(after, chunk_size, max_pages):

    base_url = 'https://export.arxiv.org/api/query'

    # Search parameters
    search_query = ARXIV_QUERY

    # Construct API query
    query = f'search_query={search_query}&sortBy=submittedDate&sortOrder=descending&max_results={chunk_size*max_pages}'

    # Fetch ATOM answer
    response = _fetch_from_arxiv_api(base_url, query)

    feed = atoma.parse_atom_bytes(response.content)

    # Extract info
    rows = []
    for i, result in enumerate(
            feed.entries
    ):
        if result.published < after:
            InfoEvent(
                msg=f"Breaking after {i} papers as published date was earlier than the window start"
            )
            break

        rows.append(
            {
                "arxiv": _extract_arxiv_id(result.id_),
                "title": sanitize_text(result.title.value),
                "abstract": sanitize_text(result.summary.value),
                "published_on": result.published,
            }
        )
    return rows


def _fetch_from_arxiv_api(base_url, query):
    for _ in range(ARXIV_NUM_RETRIES):
        try:
            response = requests.get(f"{base_url}?{query}")
        except Exception as e:
            RetryableErrorEvent("Could not get results from arxiv.", context={'exception': str(e)})
            time.sleep(ARXIV_DELAY)
        else:
            return response

    FatalErrorEvent(f"Could not get results from arxiv after {ARXIV_NUM_RETRIES} trials")
