# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

arxiv-sanity-bot is an automated system that:
1. Fetches trending AI/ML papers from alphaXiv and HuggingFace daily papers
2. Ranks papers using a scoring system (2 points if in both sources, 1 point otherwise)
3. Summarizes top-ranked papers using OpenAI API (model configured in code)
4. Extracts the first image from each paper PDF
5. Posts summaries to X/Twitter as a threaded conversation

The bot runs as a GitHub Action on a daily schedule (free compute) and uses Firebase (free tier) to track already-posted papers to prevent duplicates.

## Development Commands

### Setup
```bash
# Install production dependencies
uv sync

# Install with dev dependencies (mypy, ruff, black, pre-commit)
uv sync --group dev

# Install with test dependencies (pytest, coverage, etc.)
uv sync --extra test

# Install with both dev and test dependencies
uv sync --group dev --extra test

# Install pre-commit hooks (after installing dev dependencies)
uv run pre-commit install
```

### Testing
```bash
# Run all tests
uv run pytest

# Run with coverage
uv run pytest --cov=arxiv_sanity_bot --cov-report=html

# Run a single test file
uv run pytest tests/test_arxiv.py

# Run a specific test
uv run pytest tests/test_arxiv.py::test_function_name
```

### Code Quality
```bash
# Run ruff linter (with auto-fix)
uv run ruff check --fix

# Run black formatter
uv run black .

# Run mypy type checker
uv run mypy arxiv_sanity_bot --ignore-missing-imports

# Run pre-commit hooks manually on all files
uv run pre-commit run --all-files
```

### Running the Bot
```bash
# Run with default settings (1 week window)
uv run arxiv-sanity-bot

# Run with custom time window (hours ago)
uv run arxiv-sanity-bot --window_start 168 --window_stop 0

# Dry run (doesn't actually post tweets)
uv run arxiv-sanity-bot --dry
```

## Architecture

### Data Flow Pipeline

1. **Paper Collection** (`ranking/ranked_papers.py`):
   - Fetches papers from alphaXiv API (trending, paginated, with votes)
   - Fetches papers from HuggingFace daily papers API
   - Applies percentile filtering to alphaXiv papers (top 2% by votes)
   - Merges results and assigns scores (2 = both sources, 1 = single source)
   - Sorts by score (descending) then by average rank across sources

2. **Paper Selection** (`cli/arxiv_sanity_bot.py`):
   - Filters papers by configured time window and score threshold
   - Checks against Firebase to skip already-posted papers
   - Selects top N papers (configurable via `MAX_NUM_PAPERS`)

3. **Summarization** (`models/openai.py`):
   - Calls OpenAI API with iterative refinement loop
   - Model is hardcoded in `models/openai.py` (currently "gpt-5-mini")
   - Ensures summaries fit tweet length constraints
   - Retries with feedback if summary too long

4. **Image Extraction** (`arxiv/extract_image.py`):
   - Downloads paper PDF from arXiv
   - Extracts first meaningful image (graphs/figures, not tables)
   - Uses PyMuPDF and pypdf for PDF processing

5. **Tweet Publishing** (`twitter/send_tweet.py`):
   - Creates summary tweet about the batch
   - Posts each paper as a reply to the summary tweet
   - Attaches extracted image to each tweet
   - Posts arXiv URL as a second reply to each paper tweet
   - Stores tweet metadata in Firebase

### Key Configuration

All bot parameters are centralized in `config.py`:
- `SOURCE`: Paper source ("ranked" uses alphaXiv + HuggingFace)
- `SCORE_THRESHOLD`: Minimum score to consider (default: 1)
- `MAX_NUM_PAPERS`: How many papers to post per run (default: 7)
- `WINDOW_START/STOP`: Time window in hours (default: 168 hours/1 week ago to now)
- `ALPHAXIV_TOP_PERCENTILE`: Keep only top N% by votes (default: 98 = top 2%)

**Note:** The bot always fetches 7 days of data from APIs, then filters by the configured time window. This ensures adequate trending signal.

The OpenAI model is configured directly in `models/openai.py` (not in config.py).

### Data Models (`schemas.py`)

- `RawPaper`: Paper from API (arxiv_id, title, abstract, published_on, votes)
- `RankedPaper`: Scored paper with ranking metadata (score, alphaxiv_rank, hf_rank, source)
  - `sort_key()`: Returns `(-score, average_rank)` for sorting
  - Papers with score=2 (both sources) always rank higher than score=1

### Storage Layer

`store/store.py` provides a dict-like interface to Firebase:
- `DocumentStore[arxiv_id]`: Get/set paper metadata
- `arxiv_id in DocumentStore`: Check if paper already posted
- Credentials loaded from base64-encoded `FIREBASE_CREDENTIALS` env var

### Error Handling

- Uses `tenacity` library for retries with exponential backoff
- `AlphaXivAPIError` and `HuggingFaceAPIError` for API failures
- `FatalError` (logger.py) for unrecoverable errors
- OpenAI calls retry up to `CHATGPT_N_TRIALS` times

## Environment Variables

Required in `.env` or GitHub Secrets:
- `OPENAI_API_KEY`: OpenAI API key
- `TWITTER_CONSUMER_KEY/SECRET`: Twitter OAuth 1.0a credentials
- `TWITTER_ACCESS_TOKEN/SECRET`: Twitter OAuth 1.0a tokens
- `FIREBASE_CREDENTIALS`: Base64-encoded Firebase service account JSON

## Testing Notes

- Tests use `mock-firestore` for Firebase mocking
- Tests use `freezegun` for time mocking
- Test files mirror the structure of `arxiv_sanity_bot/` directory
- Key test fixtures handle API response mocking

## Historical Context

The bot previously used Altmetric scores for ranking (deprecated in 2024 when their API closed). The current system uses alphaXiv trending + HuggingFace daily papers, which provides better signal for ML/AI papers. The `altmetric/` module is kept for historical reference but is no longer used.
