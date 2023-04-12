from typing import List, Dict
from zoneinfo import ZoneInfo

import httpx
from datetime import datetime, tzinfo
import asyncio

from arxiv_sanity_bot.config import ALTMETRIC_CHUNK_SIZE, TIMEZONE


async def _gather_one_score(arxiv_id: str) -> Dict:

    url = f"https://api.altmetric.com/v1/arxiv/{arxiv_id}"

    # We use verify=False to avoid the SSLWantReadError error
    async with httpx.AsyncClient(verify=False) as client:
        response = await client.get(url)

    if response.status_code == 200:

        js = response.json()

        pub_on_unix = js["published_on"]

        # Let's use the cumulative score
        score = js["history"]["at"]
        pub_on = datetime.fromtimestamp(pub_on_unix, tz=TIMEZONE).isoformat()

    else:
        # Probably not yet processed
        score = -1
        pub_on = None

    return {"score": score, "published_on": pub_on}


async def gather_scores(
    arxiv_ids: List[str], chunk_size: int = ALTMETRIC_CHUNK_SIZE
) -> List[Dict]:
    """
    Gather the Altmetric history score (cumulative popularity of the paper)

    :param arxiv_ids: a list of arxiv ids
    :param chunk_size: size of each chunk. API requests within a chunk are going to be run in parallel
    :return: a list of dictionaries like {"score": score, "published_on": pub_on}
    """
    results = []
    for i in range(0, len(arxiv_ids), chunk_size):
        chunk = arxiv_ids[i:i + chunk_size]
        chunk_results = await asyncio.gather(*[_gather_one_score(x) for x in chunk])
        results.extend(chunk_results)

    assert len(results) == len(arxiv_ids)

    return results
