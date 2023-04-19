import time
import contextlib
import tweepy

from arxiv_sanity_bot.config import TWITTER_N_TRIALS, TWITTER_SLEEP_TIME
from arxiv_sanity_bot.events import InfoEvent, FatalErrorEvent, RetryableErrorEvent
from arxiv_sanity_bot.twitter.auth import TwitterOAuth1


@contextlib.contextmanager
def twitter_autoretry(error_msg):

    for i in range(TWITTER_N_TRIALS):

        try:

            yield

        except tweepy.errors.TweepyException as e:

            if (i + 1) < TWITTER_N_TRIALS:
                RetryableErrorEvent(
                    msg=f"{error_msg}. Retrying after {TWITTER_SLEEP_TIME} s",
                    context={"exception": str(e)},
                )
                time.sleep(TWITTER_SLEEP_TIME)
                continue
            else:
                FatalErrorEvent(
                    msg=f"{error_msg} after {TWITTER_N_TRIALS}",
                    context={"exception": str(e)},
                )

        else:

            break


def send_tweet(tweet: str, auth: TwitterOAuth1, img_path: str = None) -> str:
    """
    Send a tweet.

    :param tweet: tweet to send. Must respect twitter maximum length
    :param auth: an instance of a TwitterOAuth1 dataclass with credentials
    :param img_path: the path to an optional image to attach to the tweet
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
        with twitter_autoretry("Could not upload image"):

            upload = api.media_upload(img_path)

        InfoEvent(msg=f"Uploaded image {img_path} as media_id {upload.media_id_string}")

        media_ids.append(upload.media_id_string)

    client = tweepy.Client(
        consumer_key=auth.consumer_key,
        consumer_secret=auth.consumer_secret,
        access_token=auth.access_token,
        access_token_secret=auth.access_token_secret,
    )

    with twitter_autoretry("Could not send tweet"):

        response = client.create_tweet(text=tweet, media_ids=media_ids)

    InfoEvent(msg=f"Sent tweet {tweet}")

    tweet_url = f"https://twitter.com/user/status/{response.data['id']}"

    return tweet_url
