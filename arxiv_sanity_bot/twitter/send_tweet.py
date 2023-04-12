import tweepy

from arxiv_sanity_bot.events import InfoEvent
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

    response = client.create_tweet(text=tweet)

    InfoEvent(msg=f"Sent tweet {tweet}")

    tweet_url = f"https://twitter.com/user/status/{response.data['id']}"

    return tweet_url
