"""CI sanity check: post one tweet (with image) to verify Twitter auth.

Intended to be invoked from a GitHub Actions workflow_dispatch run to confirm
that the production Twitter credentials are wired up correctly. Posts a tweet
and an image upload, then prints the resulting URL. Delete the tweet from the X
UI afterwards.

Filename is deliberately NOT `test_*.py` so pytest skips it.
"""

import sys
import tempfile
from pathlib import Path

import dotenv

dotenv.load_dotenv()

from arxiv_sanity_bot.twitter.auth import TwitterOAuth1  # noqa: E402
from arxiv_sanity_bot.twitter.send_tweet import send_tweet  # noqa: E402


# Minimal 1x1 transparent PNG — enough to exercise the upload.twitter.com path
# without committing a real image to the repo.
_TINY_PNG = bytes.fromhex(
    "89504e470d0a1a0a0000000d49484452000000010000000108060000001f15c4"
    "890000000d49444154789c63f8ffff3f0005fe02fedccc59e70000000049454e"
    "44ae426082"
)


def main() -> int:
    auth = TwitterOAuth1()
    if not all(
        [
            auth.consumer_key,
            auth.consumer_secret,
            auth.access_token,
            auth.access_token_secret,
        ]
    ):
        print("Missing TWITTER_* env vars", file=sys.stderr)
        return 1

    with tempfile.TemporaryDirectory() as tmp:
        img_path = str(Path(tmp) / "tiny.png")
        Path(img_path).write_bytes(_TINY_PNG)

        text = "arxiv-sanity-bot CI auth check — please ignore"
        print(f"Posting: {text!r} with image {img_path!r} ...")

        url, tweet_id = send_tweet(text, auth, img_path=img_path)

    if url is None:
        print("send_tweet returned no URL — check logs above", file=sys.stderr)
        return 1

    print(f"OK: {url}  (id={tweet_id})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
