# Summarize the top N papers
from zoneinfo import ZoneInfo

# Papers under this score will not be posted
# NOTE: Score system changed - now 1-2 points (ranked sources) instead of Altmetric 0-100+
SCORE_THRESHOLD = 1
MAX_NUM_PAPERS = 7

# Source for the abstracts
# Options: "arxiv", "arxiv-sanity", "ranked"
# "ranked" uses alphaXiv + HuggingFace (recommended)
SOURCE = "ranked"

# Arxiv settings
ARXIV_QUERY = (
    "cat:cs.CV OR cat:cs.LG OR cat:cs.CL OR cat:cs.AI OR cat:cs.NE OR cat:cs.RO"
)
# Delay between pages requested to the Arxiv API
# It is suggested to use 3 seconds in the API terms of service
ARXIV_DELAY = 3  # seconds
# Number of times to retry a failed page fetch
ARXIV_NUM_RETRIES = 50
# Paging settings
ARXIV_PAGE_SIZE = 100  # papers
ARXIV_MAX_PAGES = 10
# Retry settings for when API returns zero results
ARXIV_ZERO_RESULTS_MAX_RETRIES = 10
ARXIV_ZERO_RESULTS_MAX_WAIT_TIME = 300  # seconds (5 minutes)

# This defines the time window to consider
WINDOW_START = 168  # hours ago (1 week)
WINDOW_STOP = 0  # hours ago

# Number of times to try calling chatGPT before giving up
# (if chatGPT returns summaries that are too long)
CHATGPT_N_TRIALS = 10
CHATGPT_SLEEP_TIME = 10

# The url length depens on the url shortener used. For tinyurl is 18 if
# we remove https://
URL_LENGTH = 0
TWEET_TEXT_LENGTH = 275 - URL_LENGTH
# How many times to try to send a tweet before failing
TWITTER_N_TRIALS = 10
# Seconds to wait if sending a tweet fails, before retrying
TWITTER_SLEEP_TIME = 60

# AlphaXiv settings
ALPHAXIV_PAGE_SIZE = 100
ALPHAXIV_MAX_PAPERS = 10000
ALPHAXIV_TOP_PERCENTILE = 98  # Keep only top 2% of papers by votes (100 - 2 = 98)
ALPHAXIV_N_RETRIES = 10
ALPHAXIV_WAIT_TIME = 20

# HuggingFace settings
HF_N_RETRIES = 10
HF_WAIT_TIME = 20

# DEPRECATED: Altmetric API closed in 2024
# How many calls we can make in parallel for the Altmetric
# API
# ALTMETRIC_CHUNK_SIZE = 50
# ALTMETRIC_N_RETRIES = 10
# ALTMETRIC_WAIT_TIME = 20

# Characters allowed in an abstract
ABSTRACT_ALLOWED_CHARACTERS = (
    "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789.,!?'- "
)

# The timezone to use for all time stamps
TIMEZONE = ZoneInfo("UTC")

# Store
FIREBASE_COLLECTION = "arxiv-papers"
