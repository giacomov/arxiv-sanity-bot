# Summarize the top N papers
from zoneinfo import ZoneInfo

PAPERS_TO_SUMMARIZE = 10

# This defines the time window to consider
WINDOW_START = 48  # hours ago
WINDOW_STOP = 24  # hours ago

# Number of times to try calling chatGPT before giving up
# (if chatGPT returns summaries that are too long)
CHATGPT_N_TRIALS = 10

# The url length depens on the url shortener used. For tinyurl is 18 if
# we remove https://
URL_LENGTH = 20
TWEET_TEXT_LENGTH = 275 - URL_LENGTH
# How many times to try to send a tweet before failing
TWITTER_N_TRIALS = 10
# Seconds to wait if sending a tweet fails, before retrying
TWITTER_SLEEP_TIME = 60

# How many calls we can make in parallel for the Altmetric
# API
ALTMETRIC_CHUNK_SIZE = 10

# Characters allowed in an abstract
ABSTRACT_ALLOWED_CHARACTERS = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789.,!?'- "

# Time to give to arxiv-sanity-lite to render the pages
# before trying to fetch them (in seconds)
ARXIV_SANITY_RENDERING_TIME = 5
# Max number of pages to fetch from arxiv-sanity in one go
ARXIV_SANITY_MAX_PAGES = 10
# How many pages to download concurrently from arxiv-sanity
ARXIV_SANITY_CONCURRENT_DOWNLOADS = 5
# How many times to retry in case of issues
ARXIV_SANITY_N_TRIALS = 10
# Seconds to wait if sending a download fails, before retrying
ARXIV_SANITY_SLEEP_TIME = 60
TIMEZONE = ZoneInfo("America/Los_Angeles")

ABSTRACT_CACHE_FILE = "posted_abstracts.parquet"
