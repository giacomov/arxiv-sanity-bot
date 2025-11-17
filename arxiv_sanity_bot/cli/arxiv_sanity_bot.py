from datetime import datetime, timedelta
import time
import random
from typing import Any

import click
import numpy as np
import pandas as pd

import dotenv
dotenv.load_dotenv()

from arxiv_sanity_bot.arxiv import arxiv_abstracts  # noqa: E402
from arxiv_sanity_bot.ranking import ranked_papers  # noqa: E402
from arxiv_sanity_bot.arxiv.extract_image import extract_first_image  # noqa: E402
from arxiv_sanity_bot.config import (  # noqa: E402
    WINDOW_START,
    WINDOW_STOP,
    TIMEZONE,
    SOURCE,
    SCORE_THRESHOLD,
    MAX_NUM_PAPERS,
)
from arxiv_sanity_bot.logger import get_logger, FatalError  # noqa: E402
from arxiv_sanity_bot.models.openai import OpenAI  # noqa: E402
from arxiv_sanity_bot.store.store import DocumentStore  # noqa: E402
from arxiv_sanity_bot.twitter.auth import TwitterOAuth1  # noqa: E402
from arxiv_sanity_bot.twitter.send_tweet import send_tweet  # noqa: E402


logger = get_logger(__name__)


_SOURCES = {
    "arxiv": arxiv_abstracts,
    "ranked": ranked_papers,
}


@click.command()
@click.option("--window_start", default=WINDOW_START, help="Window start", type=int)
@click.option("--window_stop", default=WINDOW_STOP, help="Window stop", type=int)
@click.option("--dry", is_flag=True)
def bot(window_start, window_stop, dry):
    logger.info("Bot starting")

    # This returns all abstracts above the threshold
    abstracts, n_retrieved = _gather_abstracts(window_start, window_stop)

    if abstracts.shape[0] == 0:
        return

    # Summarize the papers above the threshold that have not been summarized
    # before
    doc_store = DocumentStore.from_env_variable()

    filtered_abstracts = _keep_only_new_abstracts(abstracts, doc_store)

    summaries = _summarize_top_abstracts(filtered_abstracts)

    if len(summaries) > 0:
        send_tweets(n_retrieved, summaries, doc_store, dry)

    logger.info("Bot finishing")


def send_tweets(n_retrieved: int, summaries: list[dict[str, Any]], doc_store: DocumentStore, dry: bool):

    # Send the tweets
    oauth = TwitterOAuth1()

    if dry:
        def tweet_sender(tweet: str, auth: TwitterOAuth1, img_path: str | None = None, in_reply_to_tweet_id: int | None = None) -> tuple[str | None, int | None]:
            return ("https://fake.url", 123456789)
    else:
        tweet_sender = send_tweet

    logger.info("Sending summary tweet")
    summary_tweet = OpenAI().generate_bot_summary(n_retrieved, len(summaries))

    if summary_tweet is None:

        # Error!
        logger.critical("Could not generate summary tweet")
        raise FatalError("Could not generate summary tweet")

    _ = tweet_sender(summary_tweet, auth=oauth)

    for s in summaries[::-1]:
        # Introduce a random delay between the tweets to avoid triggering
        # the Twitter alarm
        delay = random.randint(10, 30)
        logger.info(f"Waiting for {delay} seconds before sending next tweet")
        time.sleep(delay)

        this_url, this_tweet_id = tweet_sender(
            s["tweet"], auth=oauth, img_path=s["image"]
        )

        if this_url is not None:
            if s["url"]:
                logger.info(f"Sending URL as reply to tweet {this_tweet_id}")
                time.sleep(2)
                tweet_sender(
                    s["url"], auth=oauth, in_reply_to_tweet_id=this_tweet_id
                )

            doc_store[s["arxiv"]] = {
                "tweet_id": this_tweet_id,
                "tweet_url": this_url,
                "title": s["title"],
                "published_on": s["published_on"],
            }


def _keep_only_new_abstracts(abstracts: pd.DataFrame, doc_store: DocumentStore) -> pd.DataFrame:
    mask = np.ones(len(abstracts), dtype=bool)

    for idx, (_, row) in enumerate(abstracts.iterrows()):
        if row["arxiv"] in doc_store:
            # Yes, we already processed it. Skip it
            logger.info(
                f"Paper {row['arxiv']} has been already summarized in a previous run",
                extra={"title": row["title"], "score": row["score"]},
            )
            mask[idx] = False

    return abstracts[mask].reset_index(drop=True)


def _summarize_top_abstracts(selected_abstracts: pd.DataFrame) -> list[dict[str, Any]]:
    summaries: list[dict[str, Any]] = []

    for i, row in selected_abstracts.iloc[:MAX_NUM_PAPERS].iterrows():
        summary, url, img_path = _summarize(row)

        if summary is not None:
            summaries.append(
                {
                    "arxiv": row["arxiv"],
                    "title": row["title"],
                    "score": row["score"],
                    "published_on": row["published_on"],
                    "image": img_path,
                    "tweet": summary,
                    "url": url,
                }
            )

    return summaries


def _summarize(row: pd.Series) -> tuple[str, str, str | None]:
    openai_model = OpenAI()

    summary = openai_model.summarize_abstract(row["abstract"])

    url = _SOURCES[SOURCE].get_url(row["arxiv"])

    logger.info(
        f"Processed abstract for {url}",
        extra={"title": row["title"], "score": row["score"]},
    )

    # Get image from the first page
    img_path = extract_first_image(row["arxiv"])

    return summary, url, img_path


def _gather_abstracts(window_start: int, window_stop: int) -> tuple[pd.DataFrame, int]:
    """
    Get all abstracts from arxiv-sanity from the last 48 hours above the threshold

    :return: a pandas dataframe with the papers ordered by score (best at the top)
    """

    get_all_abstracts_func = _SOURCES[SOURCE].get_all_abstracts

    now = datetime.now(tz=TIMEZONE)
    start = now - timedelta(hours=window_start)
    end = now - timedelta(hours=window_stop)

    logger.info(f"Considering time interval {start} to {end} UTC")

    abstracts = get_all_abstracts_func(after=start, before=end)  # type: pd.DataFrame

    n_retrieved = abstracts.shape[0]

    if n_retrieved == 0:
        logger.info(
            f"No abstract in the time window {start} - {end} before filtering for score."
        )

        return abstracts, 0

    print(abstracts.head())

    # Threshold on score
    idx = abstracts["score"] >= SCORE_THRESHOLD
    abstracts = abstracts[idx].reset_index(drop=True)

    if abstracts.shape[0] == 0:
        logger.info(
            f"No abstract in the time window {start} - {end} above score {SCORE_THRESHOLD}"
        )
        return abstracts, 0
    else:
        logger.info(
            f"Found {abstracts.shape[0]} abstracts in the time window {start} - {end} above score {SCORE_THRESHOLD}"
        )

    return abstracts, n_retrieved


if __name__ == "__main__":
    bot()
