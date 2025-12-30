from typing import Any
import tweepy  # type: ignore
from tenacity import (
    retry,
    stop_after_attempt,
    wait_fixed,
    retry_if_exception_type,
)

from arxiv_sanity_bot.config import TWITTER_N_TRIALS, TWITTER_SLEEP_TIME
from arxiv_sanity_bot.logger import get_logger
from arxiv_sanity_bot.twitter.auth import TwitterOAuth1


logger = get_logger(__name__)


@retry(
    retry=retry_if_exception_type(tweepy.errors.TweepyException),
    stop=stop_after_attempt(TWITTER_N_TRIALS),
    wait=wait_fixed(TWITTER_SLEEP_TIME),
    reraise=True,
)
def _create_tweet(
    client: tweepy.Client,
    text: str,
    media_ids: list[str] | None = None,
    in_reply_to_tweet_id: int | None = None,
) -> Any:
    logger.info(
        "Attempting to create tweet",
        extra={
            "has_media": media_ids is not None,
            "is_reply": in_reply_to_tweet_id is not None,
        },
    )
    return client.create_tweet(
        text=text, media_ids=media_ids, in_reply_to_tweet_id=in_reply_to_tweet_id
    )


@retry(
    retry=retry_if_exception_type(tweepy.errors.TweepyException),
    stop=stop_after_attempt(TWITTER_N_TRIALS),
    wait=wait_fixed(TWITTER_SLEEP_TIME),
    reraise=True,
)
def _upload_image_with_retry(api: tweepy.API, img_path: str) -> Any:
    return api.simple_upload(img_path)


def send_tweet(
    tweet: str,
    auth: TwitterOAuth1,
    img_path: str | None = None,
    in_reply_to_tweet_id: int | None = None,
) -> tuple[str | None, int | None]:
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

    media_ids = _upload_image(auth, img_path)

    client = tweepy.Client(
        consumer_key=auth.consumer_key,
        consumer_secret=auth.consumer_secret,
        access_token=auth.access_token,
        access_token_secret=auth.access_token_secret,
    )

    mids = media_ids if len(media_ids) > 0 else None

    try:
        response = _create_tweet(client, tweet, mids, in_reply_to_tweet_id)
    except tweepy.errors.TweepyException:
        logger.error(
            "Could not send tweet with image",
            exc_info=True,
        )
        response = _create_tweet(client, tweet, None, in_reply_to_tweet_id)

    logger.info(f"Sent tweet {tweet}")

    tweet_url = (
        f"https://twitter.com/user/status/{response.data['id']}" if response else None
    )
    tweet_id = response.data["id"] if response else None

    return tweet_url, tweet_id


def _upload_image(auth: Any, img_path: str | None) -> list[str]:
    api = tweepy.API(auth)
    media_ids: list[str] = []
    if img_path is not None:
        try:
            upload = _upload_image_with_retry(api, img_path)
            logger.info(
                f"Uploaded image {img_path} as media_id {upload.media_id_string}"
            )
            media_ids.append(upload.media_id_string)
        except tweepy.errors.TweepyException:
            logger.error(
                "Could not upload image after retries",
                exc_info=True,
                extra={"img_path": img_path},
            )
    return media_ids
