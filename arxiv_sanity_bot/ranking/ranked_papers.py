import re
import random
import time
from datetime import datetime, timedelta
from typing import Any

import numpy as np
import pandas as pd
import requests
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
)

from arxiv_sanity_bot.config import (
    ALPHAXIV_PAGE_SIZE,
    ALPHAXIV_MAX_PAPERS,
    ALPHAXIV_TOP_PERCENTILE,
    ALPHAXIV_N_RETRIES,
    ALPHAXIV_WAIT_TIME,
    HF_N_RETRIES,
    HF_WAIT_TIME,
)
from arxiv_sanity_bot.logger import get_logger, FatalError
from arxiv_sanity_bot.schemas import PaperSource, RawPaper, RankedPaper


logger = get_logger(__name__)


def _sanitize_arxiv_id(arxiv_id: str | None) -> str:
    """
    Sanitize arxiv_id by extracting only the valid ID portion.

    Valid format: YYMM.NNNNN or YYMM.NNNN (e.g., 2512.24880)

    Examples:
    - "2512.24880/sso-callback" -> "2512.24880"
    - "2512.24880v1" -> "2512.24880"

    Args:
        arxiv_id: Raw arxiv ID string from API

    Returns:
        Sanitized arxiv ID

    Raises:
        FatalError: If arxiv_id doesn't match valid format
    """
    if not arxiv_id:
        raise FatalError("Empty arxiv_id encountered")

    # Match new format: YYMM.NNNNN or YYMM.NNNN
    match = re.match(r"^(\d{4}\.\d{4,5})", arxiv_id)
    if match:
        sanitized = match.group(1)
        if sanitized != arxiv_id:
            logger.info(
                "Sanitized arxiv_id",
                extra={"original": arxiv_id, "sanitized": sanitized},
            )
        return sanitized

    # Invalid format - raise fatal error
    raise FatalError(f"Invalid arxiv_id format: {arxiv_id}")


def _from_alphaxiv(paper: dict[str, Any]) -> RawPaper | None:
    arxiv_id_raw = _extract_field(
        paper, ["universal_paper_id", "id"], nested_keys=["paper"]
    )
    arxiv_id = _sanitize_arxiv_id(arxiv_id_raw)

    metrics = paper.get("metrics", {})
    votes = metrics.get("public_total_votes", 0)

    return RawPaper(
        arxiv_id=arxiv_id,
        title=_extract_field(paper, ["title"], nested_keys=["paper"]) or "",
        abstract=_extract_field(paper, ["abstract"], nested_keys=["paper"]) or "",
        published_on=_extract_field(
            paper, ["publication_date", "publishedAt"], nested_keys=["paper"]
        )
        or "",
        votes=votes,
    )


def _from_huggingface(paper: dict[str, Any]) -> RawPaper | None:
    arxiv_id_raw = _extract_field(paper, ["id"], nested_keys=["paper"])
    arxiv_id = _sanitize_arxiv_id(arxiv_id_raw)

    return RawPaper(
        arxiv_id=arxiv_id,
        title=_extract_field(paper, ["title"], nested_keys=["paper"]) or "",
        abstract=_extract_field(paper, ["summary"], nested_keys=["paper"]) or "",
        published_on=_extract_field(paper, ["publishedAt"], nested_keys=["paper"])
        or "",
    )


class AlphaXivAPIError(Exception):
    pass


class HuggingFaceAPIError(Exception):
    pass


def _extract_field(
    data: dict[str, Any], field_names: list[str], nested_keys: list[str] | None = None
) -> str | None:
    for field_name in field_names:
        if field_name in data:
            return data[field_name]

    if nested_keys:
        for nested_key in nested_keys:
            if nested_key in data and isinstance(data[nested_key], dict):
                for field_name in field_names:
                    if field_name in data[nested_key]:
                        return data[nested_key][field_name]

    return None


@retry(
    retry=retry_if_exception_type(AlphaXivAPIError),
    stop=stop_after_attempt(ALPHAXIV_N_RETRIES),
    wait=wait_exponential(multiplier=1, min=1, max=ALPHAXIV_WAIT_TIME),
    reraise=True,
)
def _fetch_alphaxiv_page(
    page_num: int, days: int = 7, page_size: int = ALPHAXIV_PAGE_SIZE
) -> list[RawPaper]:
    url = "https://api.alphaxiv.org/papers/v3/feed"
    params = {
        "pageNum": str(page_num),
        "sort": "Hot",
        "pageSize": str(page_size),
        "interval": f"{days} Days",
        "topics": "[]",
    }

    try:
        response = requests.get(url, params=params, timeout=30)
        response.raise_for_status()
        data = response.json()
        raw_papers = data.get("papers", [])

        return [p for p in (_from_alphaxiv(raw) for raw in raw_papers) if p]
    except requests.exceptions.RequestException as e:
        logger.error(
            "Failed to fetch from alphaXiv API",
            exc_info=True,
            extra={"exception": str(e)},
        )
        raise AlphaXivAPIError(str(e))


def fetch_alphaxiv_papers(
    days: int = 7,
    max_papers: int = ALPHAXIV_MAX_PAPERS,
    top_percentile: float = ALPHAXIV_TOP_PERCENTILE,
    after: datetime | None = None,
    before: datetime | None = None,
) -> tuple[list[RawPaper], int]:
    all_papers: list[RawPaper] = []
    page_num = 0
    max_pages = (max_papers + ALPHAXIV_PAGE_SIZE - 1) // ALPHAXIV_PAGE_SIZE

    logger.info(
        f"Fetching alphaXiv papers (last {days} days, max={max_papers}, top_percentile={top_percentile})"
    )

    while len(all_papers) < max_papers:
        papers = _fetch_alphaxiv_page(page_num, days, ALPHAXIV_PAGE_SIZE)

        if not papers:
            logger.info(f"No more papers from alphaXiv at page {page_num}")
            break

        all_papers.extend(papers)
        logger.info(
            f"Fetched page {page_num}: {len(papers)} papers (total: {len(all_papers)})"
        )

        page_num += 1

        if page_num >= max_pages:
            break

        delay = random.randint(1, 3)
        time.sleep(delay)

    papers_with_votes = [p for p in all_papers if p.votes is not None]

    if not papers_with_votes:
        logger.info("No papers with vote data from alphaXiv")
        return [], 0

    # Apply date filtering if date range is provided
    if after and before:
        papers_to_filter = [
            p
            for p in papers_with_votes
            if (dt := _parse_publication_date(p.published_on)) and after <= dt <= before
        ]
    else:
        papers_to_filter = papers_with_votes

    count_before_percentile = len(papers_to_filter)
    logger.info(
        f"AlphaXiv papers in date range (before percentile filter): {count_before_percentile}"
    )

    votes = [p.votes for p in papers_to_filter if p.votes is not None]
    if not votes:
        logger.info("No papers with votes to apply percentile filter")
        return [], count_before_percentile

    vote_threshold = np.percentile(votes, top_percentile)

    filtered_papers = [
        p for p in papers_to_filter if p.votes is not None and p.votes >= vote_threshold
    ]
    logger.info(
        f"Fetched {len(all_papers)} papers from alphaXiv, "
        f"{count_before_percentile} in date range, "
        f"{len(filtered_papers)} after percentile filter (top {100-top_percentile}%, >={vote_threshold:.0f} votes)"
    )
    return filtered_papers[:max_papers], count_before_percentile


@retry(
    retry=retry_if_exception_type(HuggingFaceAPIError),
    stop=stop_after_attempt(HF_N_RETRIES),
    wait=wait_exponential(multiplier=1, min=1, max=HF_WAIT_TIME),
    reraise=True,
)
def _fetch_hf_papers_for_date(date_str: str) -> list[RawPaper]:
    url = f"https://huggingface.co/api/daily_papers?date={date_str}"

    try:
        response = requests.get(url, timeout=30)
        response.raise_for_status()
        raw_papers = response.json()

        return [p for p in (_from_huggingface(raw) for raw in raw_papers) if p]
    except requests.exceptions.RequestException as e:
        logger.error(
            f"Failed to fetch HF papers for {date_str}",
            exc_info=True,
            extra={"exception": str(e)},
        )
        raise HuggingFaceAPIError(str(e))


def fetch_hf_papers_date_range(days: int = 7) -> list[RawPaper]:
    all_papers = []
    today = datetime.now()

    logger.info(f"Fetching HuggingFace papers (last {days} days)")

    for i in range(days):
        date = (today - timedelta(days=i)).strftime("%Y-%m-%d")
        try:
            papers = _fetch_hf_papers_for_date(date)
            all_papers.extend(papers)
            logger.info(f"Fetched {len(papers)} papers from HF for {date}")

            delay = random.randint(1, 3)
            time.sleep(delay)
        except HuggingFaceAPIError as e:
            logger.error(
                f"Could not fetch HF papers for {date}, continuing",
                exc_info=True,
                extra={"exception": str(e)},
            )
            continue

    logger.info(f"Total HuggingFace papers fetched: {len(all_papers)}")
    return all_papers


def _merge_and_score_papers(
    alphaxiv_papers: list[RawPaper], hf_papers: list[RawPaper]
) -> list[RankedPaper]:
    papers: dict[str, RankedPaper] = {}

    for rank, paper in enumerate(alphaxiv_papers):
        papers[paper.arxiv_id] = RankedPaper(
            arxiv_id=paper.arxiv_id,
            title=paper.title,
            abstract=paper.abstract,
            published_on=paper.published_on,
            score=1,
            alphaxiv_rank=rank,
            hf_rank=None,
            source=PaperSource.ALPHAXIV,
        )

    for rank, paper in enumerate(hf_papers):
        if paper.arxiv_id in papers:
            papers[paper.arxiv_id].score = 2
            papers[paper.arxiv_id].hf_rank = rank
            papers[paper.arxiv_id].source = PaperSource.BOTH
        else:
            papers[paper.arxiv_id] = RankedPaper(
                arxiv_id=paper.arxiv_id,
                title=paper.title,
                abstract=paper.abstract,
                published_on=paper.published_on,
                score=1,
                hf_rank=rank,
                alphaxiv_rank=None,
                source=PaperSource.HUGGINGFACE,
            )

    return sorted(papers.values(), key=lambda p: p.sort_key())


def _parse_publication_date(date_str: str) -> datetime | None:
    try:
        return datetime.fromisoformat(date_str.replace("Z", "+00:00"))
    except (ValueError, AttributeError):
        return None


def _make_timezone_aware(dt: datetime, reference_tz) -> datetime:
    return dt if dt.tzinfo else dt.replace(tzinfo=reference_tz)


def _filter_by_date_range(
    papers: list[RankedPaper], after: datetime, before: datetime
) -> list[RankedPaper]:
    filtered = []
    for paper in papers:
        if not (published_dt := _parse_publication_date(paper.published_on)):
            logger.info(
                f"Could not parse date for {paper.arxiv_id}, skipping date filter",
                extra={"date": paper.published_on},
            )
            continue

        after_aware = _make_timezone_aware(after, published_dt.tzinfo)
        before_aware = _make_timezone_aware(before, published_dt.tzinfo)

        if after_aware <= published_dt <= before_aware:
            filtered.append(paper)

    return filtered


def _papers_to_dataframe(papers: list[RankedPaper]) -> pd.DataFrame:
    rows = []
    for paper in papers:
        published_dt = _parse_publication_date(paper.published_on)
        rows.append(
            {
                "arxiv": paper.arxiv_id,
                "title": paper.title,
                "abstract": paper.abstract,
                "published_on": published_dt if published_dt else datetime.now(),
                "score": paper.score,
                "alphaxiv_rank": paper.alphaxiv_rank,
                "hf_rank": paper.hf_rank,
                "average_rank": paper.average_rank,
            }
        )

    return pd.DataFrame(rows)


def get_all_abstracts(after: datetime, before: datetime) -> tuple[pd.DataFrame, int]:
    if after >= before:
        logger.info("Invalid time window, returning empty DataFrame")
        return pd.DataFrame(), 0

    alphaxiv_papers, alphaxiv_count_before_percentile = fetch_alphaxiv_papers(
        days=7,
        max_papers=ALPHAXIV_MAX_PAPERS,
        top_percentile=ALPHAXIV_TOP_PERCENTILE,
        after=after,
        before=before,
    )
    hf_papers = fetch_hf_papers_date_range(days=7)

    scored_papers = _merge_and_score_papers(alphaxiv_papers, hf_papers)

    if not scored_papers:
        logger.info("No papers found in time window")
        return pd.DataFrame(), 0

    filtered_papers = _filter_by_date_range(scored_papers, after, before)

    if not filtered_papers:
        logger.info("No papers in time window after date filtering")
        return pd.DataFrame(), alphaxiv_count_before_percentile

    df = _papers_to_dataframe(filtered_papers)

    logger.info(
        f"Returning {len(df)} papers sorted by score and rank",
        extra={
            "score_2": len(df[df["score"] == 2]),
            "score_1": len(df[df["score"] == 1]),
            "alphaxiv_count_before_percentile": alphaxiv_count_before_percentile,
        },
    )

    return df, alphaxiv_count_before_percentile


def get_url(arxiv_id: str) -> str:
    return f"https://arxiv.org/abs/{arxiv_id}"
