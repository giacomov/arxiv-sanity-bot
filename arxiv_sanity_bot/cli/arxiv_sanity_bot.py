import os
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import pandas as pd
import pyshorteners

from arxiv_sanity_bot.arxiv_sanity.abstracts import get_all_abstracts
from arxiv_sanity_bot.config import (
    PAPERS_TO_SUMMARIZE,
    WINDOW_START,
    WINDOW_STOP,
    TIMEZONE,
    ABSTRACT_CACHE_FILE,
)
from arxiv_sanity_bot.events import InfoEvent
from arxiv_sanity_bot.models.chatGPT import ChatGPT
from arxiv_sanity_bot.twitter.auth import TwitterOAuth1
from arxiv_sanity_bot.twitter.send_tweet import send_tweet


def bot():

    InfoEvent(msg="Bot starting")

    abstracts, start, end = _gather_abstracts()

    if abstracts.shape[0] == 0:

        InfoEvent(msg=f"No abstract in the time window {start} - {end}")

    # Summarize the top 10 papers
    summaries = _summarize_top_abstracts(abstracts, n=PAPERS_TO_SUMMARIZE)

    # Send the tweets
    oauth = TwitterOAuth1()
    for s in summaries:
        send_tweet(s, auth=oauth)

    InfoEvent(msg="Bot finishing")


def _summarize_top_abstracts(abstracts, n):

    # This is indexed by arxiv number
    already_processed_df = (
        pd.read_parquet(ABSTRACT_CACHE_FILE)
        if os.path.exists(ABSTRACT_CACHE_FILE)
        else None
    )

    s = pyshorteners.Shortener()
    chatGPT = ChatGPT()
    summaries = []
    processed = []
    for i, row in abstracts.iloc[:n].iterrows():

        if already_processed_df is not None:
            # Check if we already processed this paper
            if row["arxiv"] in already_processed_df.index:
                # Yes, we already processed it. Skip it
                InfoEvent(
                    f"Paper {row['arxiv']} was already processed in a previous run",
                    context={
                        "title": row['title'],
                        "score": row['score']
                    }
                )
                continue

        summary = chatGPT.summarize_abstract(row["abstract"])

        url = f"https://arxiv-sanity-lite.com/?rank=pid&pid={row['arxiv']}"
        # Remove the 'http://' part which is useless and consumes characters
        # for nothing
        u = s.tinyurl.short(url).split("//")[-1]

        summaries.append(f"{u} {summary}")

        processed.append(row)

    if len(processed) > 0:

        processed_df = pd.DataFrame(processed).set_index("arxiv")

        if already_processed_df is not None:
            processed_df = pd.concat([already_processed_df, processed_df])

        processed_df.to_parquet(ABSTRACT_CACHE_FILE)

    return summaries


def _gather_abstracts():
    """
    Get all abstracts from arxiv-sanity from the last 48 hours

    :return: a pandas dataframe with the papers ordered by score (best at the top)
    """
    now = datetime.now(tz=TIMEZONE)
    abstracts = get_all_abstracts(
        after=now - timedelta(hours=WINDOW_START)
    )  # type: pd.DataFrame

    if abstracts.shape[0] == 0:
        return abstracts, now - timedelta(hours=WINDOW_START), now

    # Remove abstracts newer than 24 hours (as we need at least 24 hours to accumulate some
    # stats for altmetric)
    start = now - timedelta(hours=WINDOW_START)
    end = now - timedelta(hours=WINDOW_STOP)
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
