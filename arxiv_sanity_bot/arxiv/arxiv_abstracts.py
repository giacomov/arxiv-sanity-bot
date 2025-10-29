import asyncio
from datetime import datetime
import re
import requests
import time

import pandas as pd
import arxiv
from arxiv import SortOrder
import atoma
import xml.etree.ElementTree as ET


from arxiv_sanity_bot.altmetric.scores import gather_scores
from arxiv_sanity_bot.config import (
    ARXIV_QUERY,
    ARXIV_DELAY,
    ARXIV_NUM_RETRIES,
    ARXIV_MAX_PAGES,
    ARXIV_PAGE_SIZE,
)
from arxiv_sanity_bot.events import InfoEvent, RetryableErrorEvent, FatalErrorEvent
from arxiv_sanity_bot.sanitize_text import sanitize_text


def _extract_arxiv_id(entry_id):
    return re.match(r".+abs/([0-9\.]+)(v[0-9]+)?", entry_id).groups()[0]


def get_all_abstracts(
    after,
    before,
    max_pages=ARXIV_MAX_PAGES,
    chunk_size=ARXIV_PAGE_SIZE,
) -> pd.DataFrame:

    rows = _fetch_from_arxiv_3(after, before, chunk_size * max_pages)

    InfoEvent(msg=f"Fetched {len(rows)} abstracts from Arxiv")

    if len(rows) == 0:
        return pd.DataFrame()

    abstracts = pd.DataFrame(rows)

    # Filter on time
    abstracts["published_on"] = pd.to_datetime(abstracts["published_on"])
    idx = (abstracts["published_on"] < before) & (abstracts["published_on"] > after)
    abstracts = abstracts[idx].reset_index(drop=True)

    if abstracts.shape[0] > 0:
        # Fetch scores
        scores = _fetch_scores(abstracts)

        abstracts = abstracts.merge(scores, on="arxiv")

        return abstracts.sort_values(by="score", ascending=False).reset_index(drop=True)

    else:
        return abstracts


def _fetch_from_arxiv(after, chunk_size, max_pages):

    custom_client = arxiv.Client(
        page_size=chunk_size,
        delay_seconds=ARXIV_DELAY,
        num_retries=ARXIV_NUM_RETRIES,
    )

    rows = []
    for i, result in enumerate(
            custom_client.results(
                arxiv.Search(
                    query=ARXIV_QUERY,
                    max_results=chunk_size * max_pages,
                    sort_by=arxiv.SortCriterion.SubmittedDate,
                    sort_order=SortOrder.Descending,
                )
            )
    ):
        if result.published < after:
            InfoEvent(
                msg=f"Breaking after {i} papers as published date was earlier than the window start"
            )
            break

        rows.append(
            {
                "arxiv": _extract_arxiv_id(result.entry_id),
                "title": result.title,
                "abstract": sanitize_text(result.summary),
                "published_on": result.published,
            }
        )
    return rows


def _fetch_scores(abstracts):
    scores = pd.DataFrame(asyncio.run(gather_scores(abstracts["arxiv"].tolist())))
    return scores


def get_url(arxiv_id):
    return f"https://arxiv.org/abs/{arxiv_id}"


def _fetch_from_arxiv_3(after_date, before_date, max_results=1000):
    """Original API method - kept as backup"""
    categories = "cat:cs.CV OR cat:cs.LG OR cat:cs.CL OR cat:cs.AI OR cat:cs.NE OR cat:cs.RO"
    
    def format_datetime_for_arxiv(dt_string):
        dt = datetime.fromisoformat(dt_string.replace('Z', '+00:00'))
        return dt.strftime('%Y%m%d%H%M')
    
    after_formatted = format_datetime_for_arxiv(after_date.isoformat())
    before_formatted = format_datetime_for_arxiv(before_date.isoformat())
    search_query = f"({categories}) AND submittedDate:[{after_formatted} TO {before_formatted}]"
    
    papers = []
    start = 0
    
    while True:
        params = {
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
                break
                
            for entry in entries:
                published_str = entry.find('{http://www.w3.org/2005/Atom}published').text
                published_dt = datetime.fromisoformat(published_str.replace('Z', '+00:00'))
                
                after_dt = datetime.fromisoformat(after_date.isoformat().replace('Z', '+00:00'))
                before_dt = datetime.fromisoformat(before_date.isoformat().replace('Z', '+00:00'))
                
                if not (after_dt <= published_dt <= before_dt):
                    continue
                    
                paper_info = {
                    'arxiv': _extract_arxiv_id(entry.find('{http://www.w3.org/2005/Atom}id').text),
                    'title': entry.find('{http://www.w3.org/2005/Atom}title').text.strip(),
                    'abstract': entry.find('{http://www.w3.org/2005/Atom}summary').text.strip(),
                    'published_on': entry.find('{http://www.w3.org/2005/Atom}published').text,
                    'categories': [cat.get('term') for cat in entry.findall('{http://arxiv.org/schemas/atom}primary_category')]
                }
                papers.append(paper_info)
            
            if len(entries) < max_results:
                break
                
            start += max_results
            time.sleep(1)
            
        except Exception as e:
            print(f"API error: {e}")
            break
    
    return papers



def _fetch_from_arxiv_api(base_url, query):
    for _ in range(ARXIV_NUM_RETRIES):
        try:
            response = requests.get(base_url, params=query)
            response.raise_for_status()  # Raise an error for bad responses
        except Exception as e:
            RetryableErrorEvent("Could not get results from arxiv.", context={'exception': str(e)})
            time.sleep(ARXIV_DELAY)
        else:
            return response

    FatalErrorEvent(f"Could not get results from arxiv after {ARXIV_NUM_RETRIES} trials")
