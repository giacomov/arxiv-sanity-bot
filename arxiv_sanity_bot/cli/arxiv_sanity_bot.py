import os
from datetime import datetime, timedelta
import time

import click
import pandas as pd
import pyshorteners
import requests.exceptions

from arxiv_sanity_bot.arxiv_sanity import arxiv_sanity_abstracts
from arxiv_sanity_bot.arxiv import arxiv_abstracts
from arxiv_sanity_bot.arxiv.extract_image import extract_first_image
from arxiv_sanity_bot.config import (
    PAPERS_TO_SUMMARIZE,
    WINDOW_START,
    WINDOW_STOP,
    TIMEZONE,
    ABSTRACT_CACHE_FILE, SOURCE,
)
from arxiv_sanity_bot.events import InfoEvent, RetryableErrorEvent
from arxiv_sanity_bot.models.chatGPT import ChatGPT
from arxiv_sanity_bot.twitter.auth import TwitterOAuth1
from arxiv_sanity_bot.twitter.send_tweet import send_tweet


_SOURCES = {
    "arxiv-sanity": arxiv_sanity_abstracts,
    "arxiv": arxiv_abstracts
}


@click.command()
@click.option('--window_start', default=WINDOW_START, help='Window start', type=int)
@click.option('--window_stop', default=WINDOW_STOP, help='Window stop', type=int)
def bot(window_start, window_stop):

    InfoEvent(msg="Bot starting")

    abstracts, start, end = _gather_abstracts(window_start, window_stop)

    if abstracts.shape[0] == 0:

        InfoEvent(msg=f"No abstract in the time window {start} - {end}")
        return

    # Summarize the top 10 papers
    summaries, images = _summarize_top_abstracts(abstracts, n=PAPERS_TO_SUMMARIZE)

    # Send the tweets
    oauth = TwitterOAuth1()

    # First send summary tweet
    if len(summaries) > 0:
        InfoEvent("Sending summary tweet")
        summary_tweet = ChatGPT().generate_bot_summary(abstracts.shape[0], len(summaries))
        url, tweet_id = send_tweet(summary_tweet, auth=oauth)

        for s, img in zip(summaries, images):

            send_tweet(s, auth=oauth, img_path=img,  in_reply_to_tweet_id=tweet_id)

            time.sleep(1)

    InfoEvent(msg="Bot finishing")


def _summarize_top_abstracts(abstracts, n):

    # This is indexed by arxiv number
    already_processed_df = (
        pd.read_parquet(ABSTRACT_CACHE_FILE)
        if os.path.exists(ABSTRACT_CACHE_FILE)
        else None
    )

    summaries = []
    images = []
    processed = []
    for i, row in abstracts.iloc[:n].iterrows():

        summary, short_url, img_path = _summarize_if_new(already_processed_df, row)

        if summary is not None:
            summaries.append(f"{short_url} {summary}")
            images.append(img_path)
            processed.append(row)

    _save_to_cache(already_processed_df, processed)

    return summaries, images


def _save_to_cache(already_processed_df, processed):
    if len(processed) > 0:

        processed_df = pd.DataFrame(processed).set_index("arxiv")

        if already_processed_df is not None:
            processed_df = pd.concat([already_processed_df, processed_df])

        processed_df.to_parquet(ABSTRACT_CACHE_FILE)


def _summarize_if_new(already_processed_df, row):

    chatGPT = ChatGPT()
    s = pyshorteners.Shortener()

    if already_processed_df is not None and row["arxiv"] in already_processed_df.index:
        # Yes, we already processed it. Skip it
        InfoEvent(
            f"Paper {row['arxiv']} was already processed in a previous run",
            context={"title": row["title"], "score": row["score"]},
        )
        summary, short_url, img_path = None, None, None
    else:
        summary = chatGPT.summarize_abstract(row["abstract"])

        for _ in range(10):
            # Remove the 'http://' part which is useless and consumes characters
            # for nothing
            url = _SOURCES[SOURCE].get_url(row['arxiv'])
            try:
                short_url = s.tinyurl.short(url).split("//")[-1]
            except requests.exceptions.Timeout as e:
                RetryableErrorEvent(
                    msg="Could not shorten URL", context={"url": url, "error": str(e)}
                )
                time.sleep(10)
                continue
            else:
                InfoEvent(msg=f"Processed abstract for {url}")
                break
        else:
            InfoEvent("Could not shorten URL. Dropping it from the tweet!")
            short_url = ""

        # Get image from the first page
        img_path = extract_first_image(row['arxiv'])

    return summary, short_url, img_path


def _gather_abstracts(window_start, window_stop):
    """
    Get all abstracts from arxiv-sanity from the last 48 hours

    :return: a pandas dataframe with the papers ordered by score (best at the top)
    """

    get_all_abstracts = _SOURCES[SOURCE].get_all_abstracts

    now = datetime.now(tz=TIMEZONE)
    abstracts = get_all_abstracts(
        after=now - timedelta(hours=window_start)
    )  # type: pd.DataFrame

    if abstracts.shape[0] == 0:
        return abstracts, now - timedelta(hours=window_start), now

    # Remove abstracts newer than 24 hours (as we need at least 24 hours to accumulate some
    # stats for altmetric)
    start = now - timedelta(hours=window_start)
    end = now - timedelta(hours=window_stop)
    abstracts.query(
        "published_on.between(@start, @end)",
        inplace=True,
        local_dict={
            "start": start,
            "end": end,
        },
    )
    return abstracts, start, end


if __name__ == "__main__":

    bot()
