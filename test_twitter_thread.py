#!/usr/bin/env python3
"""
Test script to verify Twitter threading works correctly.
This will post a test tweet and reply to it.
"""
import time
from arxiv_sanity_bot.twitter.auth import TwitterOAuth1
from arxiv_sanity_bot.twitter.send_tweet import send_tweet

def test_twitter_thread():
    print("🧪 Testing Twitter threading functionality...\n")

    # Get credentials from environment
    auth = TwitterOAuth1()

    # First tweet (main summary with mock content)
    first_tweet = "🧪 Test tweet: This is a simulated paper summary to test the threading functionality."
    print(f"📤 Sending first tweet: {first_tweet}")

    first_url, first_id = send_tweet(first_tweet, auth=auth)

    if first_url is None:
        print("❌ Failed to send first tweet!")
        return False

    print(f"✅ First tweet sent!")
    print(f"   URL: {first_url}")
    print(f"   ID: {first_id}\n")

    # Wait a moment
    print("⏳ Waiting 3 seconds before sending reply...")
    time.sleep(3)

    # Reply with URL
    reply_tweet = "https://arxiv.org/abs/2304.09167"
    print(f"📤 Sending reply: {reply_tweet}")

    reply_url, reply_id = send_tweet(
        reply_tweet,
        auth=auth,
        in_reply_to_tweet_id=first_id
    )

    if reply_url is None:
        print("❌ Failed to send reply tweet!")
        return False

    print(f"✅ Reply tweet sent!")
    print(f"   URL: {reply_url}")
    print(f"   ID: {reply_id}\n")

    print("=" * 60)
    print("✅ SUCCESS! Thread created successfully!")
    print("=" * 60)
    print(f"\n🔗 Check your thread at: {first_url}")
    print(f"\n💡 The reply should appear as a thread under the first tweet.")
    print(f"   If you don't see it threaded, check your Twitter notifications.")

    return True

if __name__ == "__main__":
    try:
        success = test_twitter_thread()
        if not success:
            print("\n❌ Test failed!")
            exit(1)
    except Exception as e:
        print(f"\n❌ Error during test: {e}")
        import traceback
        traceback.print_exc()
        exit(1)
