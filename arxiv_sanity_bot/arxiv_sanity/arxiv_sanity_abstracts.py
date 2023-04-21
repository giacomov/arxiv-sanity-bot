import time

import pandas as pd
from datetime import datetime, timedelta

from requests_html import AsyncHTMLSession

from arxiv_sanity_bot.altmetric.scores import gather_scores
from arxiv_sanity_bot.config import (
    ARXIV_SANITY_RENDERING_TIME,
    ARXIV_SANITY_MAX_PAGES,
    ARXIV_SANITY_CONCURRENT_DOWNLOADS,
    TIMEZONE,
    ARXIV_SANITY_N_TRIALS,
    ARXIV_SANITY_SLEEP_TIME,
    WINDOW_START,
)
from arxiv_sanity_bot.events import InfoEvent, FatalErrorEvent
from arxiv_sanity_bot.sanitize_text import sanitize_text


def _extract_arxiv_number(title):
    href = title.find("a")[0].attrs["href"]
    # http://arxiv.org/abs/2303.11177

    return href.split("/")[-1]


async def get_abstracts_from_page(
    async_session, url, sleep_seconds=ARXIV_SANITY_RENDERING_TIME
):
    InfoEvent(msg=f"Retrieving url {url}")

    for i in range(ARXIV_SANITY_N_TRIALS):
        try:
            r = await async_session.get(url)

            await r.html.arender(sleep=sleep_seconds)
        except Exception:
            time.sleep(ARXIV_SANITY_SLEEP_TIME)
            continue
        else:
            break
    else:
        FatalErrorEvent(
            msg=f"Could not download page after {ARXIV_SANITY_N_TRIALS} trials",
            context={"url": url},
        )

    abstracts = r.html.find(".rel_abs")
    titles = r.html.find(".rel_title")

    arxiv_ids = [_extract_arxiv_number(x) for x in titles]
    scores = await gather_scores(arxiv_ids)

    abstracts = [
        {
            "arxiv": i,
            "title": sanitize_text(t.text),
            "abstract": sanitize_text(a.text),
            "score": s["score"],
            "published_on": s["published_on"],
        }
        for i, t, a, s in zip(arxiv_ids, titles, abstracts, scores)
    ]

    InfoEvent(f"Found {len(abstracts)} abstracts")

    return abstracts


def bulk_download(urls):
    asession = AsyncHTMLSession()

    list_of_lambdas = [
        lambda url=url: get_abstracts_from_page(asession, url) for url in urls
    ]

    return sum(asession.run(*list_of_lambdas), [])


def get_all_abstracts(
    max_pages=ARXIV_SANITY_MAX_PAGES,
    after=None,
    chunk_size=ARXIV_SANITY_CONCURRENT_DOWNLOADS,
):
    if after is None:
        after = datetime.now(tz=TIMEZONE) - timedelta(hours=WINDOW_START)

    abstracts = []

    for page in range(1, max_pages + 1, chunk_size):
        InfoEvent(msg=f"Processing pages {page} - {page + chunk_size - 1}")

        urls = [
            f"https://arxiv-sanity-lite.com/?q=&svm_c=0.01&page_number={x}"
            for x in range(page, page + chunk_size)
        ]

        assert len(urls) > 0

        results = bulk_download(urls)

        abstracts.extend(results)

    df = pd.DataFrame(abstracts)

    if df.shape[0] == 0:
        return df

    df["published_on"] = pd.to_datetime(df["published_on"])

    # Filter by time window
    idx = df["published_on"] > after

    return df[idx].sort_values(by="score", ascending=False).reset_index(drop=True)


def get_url(arxiv_id):
    return f"https://arxiv-sanity-lite.com/?rank=pid&pid={arxiv_id}"
