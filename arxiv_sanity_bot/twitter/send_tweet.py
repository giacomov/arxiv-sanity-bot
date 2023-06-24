import time
from typing import Tuple
import tweepy

from arxiv_sanity_bot.config import TWITTER_N_TRIALS, TWITTER_SLEEP_TIME
from arxiv_sanity_bot.events import InfoEvent, FatalErrorEvent, RetryableErrorEvent
from arxiv_sanity_bot.twitter.auth import TwitterOAuth1


def twitter_autoretry(functor, error_msg):
    for i in range(TWITTER_N_TRIALS):
        try:
            return functor()

        except tweepy.errors.TweepyException as e:
            if (i + 1) < TWITTER_N_TRIALS:
                RetryableErrorEvent(
                    msg=f"{error_msg}. Retrying after {TWITTER_SLEEP_TIME} s",
                    context={"exception": str(e)},
                )
                time.sleep(TWITTER_SLEEP_TIME)
                continue
            else:
                InfoEvent(
                    msg=f"{error_msg} after {TWITTER_N_TRIALS}. Giving up.",
                    context={"exception": str(e)},
                )


def send_tweet(
    tweet: str,
    auth: TwitterOAuth1,
    img_path: str = None,
    in_reply_to_tweet_id: int = None,
) -> Tuple[str, int]:
    """
    Send a tweet.

    :param tweet: tweet to send. Must respect twitter maximum length
    :param auth: an instance of a TwitterOAuth1 dataclass with credentials
    :param img_path: the path to an optional image to attach to the tweet
    :param in_reply_to_tweet_id: the id of the tweet to reply to, if any.
    :return: the URL of the tweet
    """

    auth = tweepy.OAuth1UserHandler(
        auth.consumer_key,
        auth.consumer_secret,
        auth.access_token,
        auth.access_token_secret,
    )

    api = tweepy.API(auth)

    media_ids = []
    if img_path is not None:
        upload = twitter_autoretry(
            lambda: api.simple_upload(img_path), "Could not upload image"
        )

        InfoEvent(msg=f"Uploaded image {img_path} as media_id {upload.media_id_string}")

        media_ids.append(upload.media_id_string)

    client = tweepy.Client(
        consumer_key=auth.consumer_key,
        consumer_secret=auth.consumer_secret,
        access_token=auth.access_token,
        access_token_secret=auth.access_token_secret,
    )

    mids = media_ids if len(media_ids) > 0 else None

    response = twitter_autoretry(
        lambda: client.create_tweet(
            text=tweet, media_ids=mids, in_reply_to_tweet_id=in_reply_to_tweet_id
        ),
        "Could not send tweet",
    )

    if response is None:

        # Twitter sometimes removes images because they are falsely classified as spam.
        # Try sending the tweet without image
        response = twitter_autoretry(
            lambda: client.create_tweet(
                text=tweet, in_reply_to_tweet_id=in_reply_to_tweet_id
            ),
            "Could not send tweet even without image",
        )

    InfoEvent(msg=f"Sent tweet {tweet}")

    tweet_url = f"https://twitter.com/user/status/{response.data['id']}" if response else None
    tweet_id = response.data["id"] if response else None

    return tweet_url, tweet_id
