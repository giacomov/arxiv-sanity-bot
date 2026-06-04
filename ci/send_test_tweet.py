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
from PIL import Image, ImageDraw

dotenv.load_dotenv()

from arxiv_sanity_bot.twitter.auth import TwitterOAuth1  # noqa: E402
from arxiv_sanity_bot.twitter.send_tweet import send_tweet  # noqa: E402


def _write_placeholder_png(path: str) -> None:
    # Twitter's media endpoint rejects degenerate (1x1) PNGs as "media type
    # unrecognized", so generate a real 256x256 image on the fly.
    img = Image.new("RGB", (256, 256), (30, 30, 60))
    draw = ImageDraw.Draw(img)
    draw.text((16, 120), "arxiv-sanity-bot CI", fill=(220, 220, 220))
    img.save(path, "PNG")


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
        img_path = str(Path(tmp) / "placeholder.png")
        _write_placeholder_png(img_path)

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
