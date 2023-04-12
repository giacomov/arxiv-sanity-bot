from arxiv_sanity_bot.twitter.auth import TwitterOAuth1


def test_twitter_oauth1_default_values(monkeypatch):
    monkeypatch.delenv("TWITTER_CONSUMER_KEY", raising=False)
    monkeypatch.delenv("TWITTER_CONSUMER_SECRET", raising=False)
    monkeypatch.delenv("TWITTER_ACCESS_TOKEN", raising=False)
    monkeypatch.delenv("TWITTER_ACCESS_TOKEN_SECRET", raising=False)

    oauth1 = TwitterOAuth1()

    assert oauth1.consumer_key == ""
    assert oauth1.consumer_secret == ""
    assert oauth1.access_token == ""
    assert oauth1.access_token_secret == ""


def test_twitter_oauth1_environment_variables(monkeypatch):
    monkeypatch.setenv("TWITTER_CONSUMER_KEY", "test_consumer_key")
    monkeypatch.setenv("TWITTER_CONSUMER_SECRET", "test_consumer_secret")
    monkeypatch.setenv("TWITTER_ACCESS_TOKEN", "test_access_token")
    monkeypatch.setenv("TWITTER_ACCESS_TOKEN_SECRET", "test_access_token_secret")

    oauth1 = TwitterOAuth1()

    assert oauth1.consumer_key == "test_consumer_key"
    assert oauth1.consumer_secret == "test_consumer_secret"
    assert oauth1.access_token == "test_access_token"
    assert oauth1.access_token_secret == "test_access_token_secret"
