import os
from datetime import datetime, timedelta, timezone
import time
import random
import click
import pandas as pd
import pyshorteners
import requests.exceptions

from arxiv_sanity_bot.arxiv_sanity import arxiv_sanity_abstracts
from arxiv_sanity_bot.arxiv import arxiv_abstracts
from arxiv_sanity_bot.arxiv.extract_image import extract_first_image
from arxiv_sanity_bot.config import (
    WINDOW_START,
    WINDOW_STOP,
    TIMEZONE,
    SOURCE,
    SCORE_THRESHOLD, MAX_NUM_PAPERS,
)
from arxiv_sanity_bot.events import InfoEvent, RetryableErrorEvent
from arxiv_sanity_bot.models.chatGPT import ChatGPT
from arxiv_sanity_bot.store.store import DocumentStore
from arxiv_sanity_bot.twitter.auth import TwitterOAuth1
from arxiv_sanity_bot.twitter.send_tweet import send_tweet


_SOURCES = {"arxiv-sanity": arxiv_sanity_abstracts, "arxiv": arxiv_abstracts}


@click.command()
@click.option("--window_start", default=WINDOW_START, help="Window start", type=int)
@click.option("--window_stop", default=WINDOW_STOP, help="Window stop", type=int)
@click.option('--dry', is_flag=True)
def bot(window_start, window_stop, dry):
    InfoEvent(msg="Bot starting")

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

    InfoEvent(msg="Bot finishing")


def send_tweets(n_retrieved, summaries, doc_store, dry):
    InfoEvent("Sending summary tweet")
    summary_tweet = ChatGPT().generate_bot_summary(n_retrieved, len(summaries))
    # Send the tweets
    oauth = TwitterOAuth1()

    if dry:
        tweet_sender = lambda *args, **kwargs: ("https://fake.url", "123456789")
    else:
        tweet_sender = send_tweet

    url, tweet_id = tweet_sender(summary_tweet, auth=oauth)

    for s in summaries[::-1]:

        # Introduce a random delay between the tweets to avoid triggering
        # the Twitter alarm
        delay = random.randint(10, 30)
        InfoEvent(msg=f"Waiting for {delay} seconds before sending next tweet")
        time.sleep(delay)

        this_url, this_tweet_id = tweet_sender(
            s["tweet"], auth=oauth, img_path=s["image"]
        )  # , in_reply_to_tweet_id=tweet_id

        if this_url is not None:
            doc_store[s["arxiv"]] = {
                "tweet_id": this_tweet_id,
                "tweet_url": this_url,
                "title": s["title"],
                "published_on": s["published_on"],
            }


def _keep_only_new_abstracts(abstracts, doc_store):

    abstracts['new'] = True

    for _, row in abstracts.iterrows():

        if row["arxiv"] in doc_store:
            # Yes, we already processed it. Skip it
            InfoEvent(
                f"Paper {row['arxiv']} has been already summarized in a previous run",
                context={"title": row["title"], "score": row["score"]},
            )

            row['new'] = False

    return abstracts[abstracts['new']].reset_index(drop=True)


def _summarize_top_abstracts(selected_abstracts):

    summaries = []

    n_summarized = 0

    for i, row in selected_abstracts.iterrows():
        summary, short_url, img_path = _summarize(row)

        if summary is not None:
            summaries.append(
                {
                    "arxiv": row["arxiv"],
                    "title": row["title"],
                    "score": row["score"],
                    "published_on": row["published_on"],
                    "image": img_path,
                    "tweet": f"{short_url} {summary}",
                }
            )
            n_summarized += 1

            if n_summarized > MAX_NUM_PAPERS:
                break

    return summaries


def _summarize(row):

    chatGPT = ChatGPT()
    s = pyshorteners.Shortener(timeout=20)

    summary = chatGPT.summarize_abstract(row["abstract"])

    for _ in range(10):
        # Remove the 'http://' part which is useless and consumes characters
        # for nothing
        url = _SOURCES[SOURCE].get_url(row["arxiv"])
        try:
            short_url = s.tinyurl.short(url).split("//")[-1]
        except requests.exceptions.Timeout as e:
            RetryableErrorEvent(
                msg="Could not shorten URL", context={"url": url, "error": str(e)}
            )
            time.sleep(10)
            continue
        else:
            InfoEvent(
                msg=f"Processed abstract for {url}",
                context={"title": row["title"], "score": row["score"]},
            )
            break
    else:
        InfoEvent("Could not shorten URL. Dropping it from the tweet!")
        short_url = ""

    # Get image from the first page
    img_path = extract_first_image(row["arxiv"])

    return summary, short_url, img_path

        
def _gather_abstracts(window_start, window_stop):
    """
    Get all abstracts from arxiv-sanity from the last 48 hours above the threshold

    :return: a pandas dataframe with the papers ordered by score (best at the top)
    """

    get_all_abstracts_func = _SOURCES[SOURCE].get_all_abstracts

    now = datetime.now(tz=TIMEZONE)
    start = now - timedelta(hours=window_start)
    end = now - timedelta(hours=window_stop)

    InfoEvent(msg=f"Considering time interval {start} to {end} UTC")

    abstracts = get_all_abstracts_func(
        after=start,
        before=end
    )  # type: pd.DataFrame

    n_retrieved = abstracts.shape[0]

    if n_retrieved == 0:

        InfoEvent(
            msg=f"No abstract in the time window {start} - {end} before filtering for score."
        )

        return abstracts, 0

    print(abstracts.head())

    # Threshold on score
    idx = abstracts["score"] >= SCORE_THRESHOLD
    abstracts = abstracts[idx].reset_index(drop=True)

    if abstracts.shape[0] == 0:
        InfoEvent(
            msg=f"No abstract in the time window {start} - {end} above score {SCORE_THRESHOLD}"
        )
        return abstracts, 0
    else:
        InfoEvent(
            msg=f"Found {abstracts.shape[0]} abstracts in the time window {start} - {end} above score {SCORE_THRESHOLD}"
        )

    return abstracts, n_retrieved


if __name__ == "__main__":
    bot()
