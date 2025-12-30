import asyncio
from datetime import datetime
import re
import requests
import time
from typing import Any

import pandas as pd
import xml.etree.ElementTree as ET
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
    RetryCallState,
)


from arxiv_sanity_bot.altmetric.scores import gather_scores
from arxiv_sanity_bot.config import (
    ARXIV_DELAY,
    ARXIV_NUM_RETRIES,
    ARXIV_MAX_PAGES,
    ARXIV_PAGE_SIZE,
    ARXIV_ZERO_RESULTS_MAX_RETRIES,
    ARXIV_ZERO_RESULTS_MAX_WAIT_TIME,
)
from arxiv_sanity_bot.logger import get_logger, FatalError
from arxiv_sanity_bot.schemas import ArxivPaper


logger = get_logger(__name__)


class ArxivZeroResultsError(Exception):
    pass


def _log_retry_attempt(retry_state: RetryCallState) -> None:
    wait_time = retry_state.next_action.sleep if retry_state.next_action else 0
    exception_str = str(retry_state.outcome.exception()) if retry_state.outcome else "Unknown"
    logger.error(
        f"Arxiv API returned zero results. Retrying in {wait_time:.1f}s (attempt {retry_state.attempt_number}/{ARXIV_ZERO_RESULTS_MAX_RETRIES})",
        exc_info=True,
        extra={"exception": exception_str},
    )


def _extract_arxiv_id(entry_id: str) -> str:
    match = re.match(r".+abs/([0-9\.]+)(v[0-9]+)?", entry_id)
    return match.groups()[0] if match else ""


def get_all_abstracts(
    after: datetime,
    before: datetime,
    max_pages: int = ARXIV_MAX_PAGES,
    chunk_size: int = ARXIV_PAGE_SIZE,
) -> tuple[pd.DataFrame, int]:

    rows = _fetch_from_arxiv(after, before, chunk_size * max_pages)

    logger.info(f"Fetched {len(rows)} abstracts from Arxiv")

    if len(rows) == 0:
        return pd.DataFrame(), 0

    abstracts = pd.DataFrame(rows)

    # Filter on time (already datetime from Pydantic model)
    idx = (abstracts["published_on"] < before) & (abstracts["published_on"] > after)
    abstracts = abstracts[idx].reset_index(drop=True)

    count = abstracts.shape[0]

    if count > 0:
        # Fetch scores
        scores = _fetch_scores(abstracts)

        abstracts = abstracts.merge(scores, on="arxiv")

        return abstracts.sort_values(by="score", ascending=False).reset_index(drop=True), count

    else:
        return abstracts, count


def _fetch_scores(abstracts: pd.DataFrame) -> pd.DataFrame:
    scores = pd.DataFrame(asyncio.run(gather_scores(abstracts["arxiv"].tolist())))
    return scores


def get_url(arxiv_id: str) -> str:
    return f"https://arxiv.org/abs/{arxiv_id}"


@retry(
    retry=retry_if_exception_type(ArxivZeroResultsError),
    stop=stop_after_attempt(ARXIV_ZERO_RESULTS_MAX_RETRIES),
    wait=wait_exponential(multiplier=1, min=1, max=min(64, ARXIV_ZERO_RESULTS_MAX_WAIT_TIME)),
    before_sleep=_log_retry_attempt,
    reraise=True,
)
def _fetch_from_arxiv(after_date: datetime, before_date: datetime, max_results: int = 1000) -> list[dict[str, Any]]:
    category_query = "cat:cs.CV OR cat:cs.LG OR cat:cs.CL OR cat:cs.AI OR cat:cs.NE OR cat:cs.RO"

    def format_datetime_for_arxiv(dt_string: str) -> str:
        dt = datetime.fromisoformat(dt_string.replace('Z', '+00:00'))
        return dt.strftime('%Y%m%d%H%M')

    after_formatted = format_datetime_for_arxiv(after_date.isoformat())
    before_formatted = format_datetime_for_arxiv(before_date.isoformat())
    search_query = f"({category_query}) AND submittedDate:[{after_formatted} TO {before_formatted}]"
    
    papers: list[dict[str, Any]] = []
    start: int = 0
    
    while True:
        params: dict[str, str | int] = {
            'search_query': search_query,
            'start': start,
            'max_results': max_results,
            'sortBy': 'submittedDate',
            'sortOrder': 'ascending'
        }

        print(params)
        
        try:
            response = requests.get("http://export.arxiv.org/api/query", params=params, timeout=30)
            response.raise_for_status()
            
            root = ET.fromstring(response.content)
            entries = root.findall('{http://www.w3.org/2005/Atom}entry')

            print(f"Fetched {len(entries)} entries from Arxiv API starting at {start}")

            if not entries:
                if start == 0:
                    raise ArxivZeroResultsError("Arxiv API returned zero results")
                break
                
            for entry in entries:
                published_elem = entry.find('{http://www.w3.org/2005/Atom}published')
                if published_elem is None or published_elem.text is None:
                    continue
                published_str = published_elem.text
                published_dt = datetime.fromisoformat(published_str.replace('Z', '+00:00'))

                after_dt = datetime.fromisoformat(after_date.isoformat().replace('Z', '+00:00'))
                before_dt = datetime.fromisoformat(before_date.isoformat().replace('Z', '+00:00'))

                if not (after_dt <= published_dt <= before_dt):
                    continue

                id_elem = entry.find('{http://www.w3.org/2005/Atom}id')
                title_elem = entry.find('{http://www.w3.org/2005/Atom}title')
                summary_elem = entry.find('{http://www.w3.org/2005/Atom}summary')

                if id_elem is None or id_elem.text is None:
                    continue
                if title_elem is None or title_elem.text is None:
                    continue
                if summary_elem is None or summary_elem.text is None:
                    continue

                try:
                    categories = [
                        cat_term for cat in entry.findall('{http://arxiv.org/schemas/atom}primary_category')
                        if (cat_term := cat.get('term')) is not None
                    ]
                    paper = ArxivPaper(
                        arxiv=_extract_arxiv_id(id_elem.text),
                        title=title_elem.text.strip(),
                        abstract=summary_elem.text.strip(),
                        published_on=published_dt,
                        categories=categories
                    )
                    papers.append(paper.model_dump())
                except Exception as e:
                    logger.error("Failed to parse paper", exc_info=True, extra={"exception": str(e)})
                    continue
            
            if len(entries) < max_results:
                break
                
            start += max_results
            time.sleep(1)
            
        except ArxivZeroResultsError:
            raise
        except Exception as e:
            print(f"API error: {e}")
            break

    return papers



def _fetch_from_arxiv_api(base_url: str, query: dict[str, Any]) -> requests.Response | None:
    for _ in range(ARXIV_NUM_RETRIES):
        try:
            response = requests.get(base_url, params=query)
            response.raise_for_status()  # Raise an error for bad responses
        except Exception as e:
            logger.error("Could not get results from arxiv.", exc_info=True, extra={'exception': str(e)})
            time.sleep(ARXIV_DELAY)
        else:
            return response

    logger.critical(f"Could not get results from arxiv after {ARXIV_NUM_RETRIES} trials")
    raise FatalError(f"Could not get results from arxiv after {ARXIV_NUM_RETRIES} trials")
