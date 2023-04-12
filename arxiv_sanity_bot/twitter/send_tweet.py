import time

import tweepy

from arxiv_sanity_bot.config import TWITTER_N_TRIALS, TWITTER_SLEEP_TIME
from arxiv_sanity_bot.events import InfoEvent, FatalErrorEvent, RetryableErrorEvent
from arxiv_sanity_bot.twitter.auth import TwitterOAuth1


def send_tweet(tweet: str, auth: TwitterOAuth1) -> str:
    """
    Send a tweet.

    :param tweet: tweet to send. Must respect twitter maximum length
    :param auth: an instance of a TwitterOAuth1 dataclass with credentials
    :return: the URL of the tweet
    """
    client = tweepy.Client(
        consumer_key=auth.consumer_key,
        consumer_secret=auth.consumer_secret,
        access_token=auth.access_token,
        access_token_secret=auth.access_token_secret,
    )

    for i in range(TWITTER_N_TRIALS):
        try:

            response = client.create_tweet(text=tweet)

        except tweepy.errors.BadRequest as e:

            if (i + 1) < TWITTER_N_TRIALS:
                RetryableErrorEvent(
                    msg=f"Could not send tweet. Retrying after {TWITTER_SLEEP_TIME} s",
                    context={"exception": str(e), "tweet": tweet},
                )
                time.sleep(TWITTER_SLEEP_TIME)
                continue
            else:
                FatalErrorEvent(
                    msg=f"Could not send tweet after {TWITTER_N_TRIALS}",
                    context={"exception": str(e), "tweet": tweet},
                )

        else:

            break

    InfoEvent(msg=f"Sent tweet {tweet}")

    tweet_url = f"https://twitter.com/user/status/{response.data['id']}"

    return tweet_url
