import dataclasses
import os


@dataclasses.dataclass
class TwitterOAuth1:

    consumer_key: str = None
    consumer_secret: str = None
    access_token: str = None
    access_token_secret: str = None

    def __post_init__(self):
        self.consumer_key = os.environ.get("TWITTER_CONSUMER_KEY", "")
        self.consumer_secret = os.environ.get("TWITTER_CONSUMER_SECRET", "")
        self.access_token = os.environ.get("TWITTER_ACCESS_TOKEN", "")
        self.access_token_secret = os.environ.get("TWITTER_ACCESS_TOKEN_SECRET", "")
