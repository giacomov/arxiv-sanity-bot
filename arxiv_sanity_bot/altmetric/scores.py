import random
import time
from typing import List, Dict

import httpx
import asyncio

from arxiv_sanity_bot.config import (
    ALTMETRIC_CHUNK_SIZE,
    ALTMETRIC_N_RETRIES,
    ALTMETRIC_WAIT_TIME,
)
from arxiv_sanity_bot.events import InfoEvent, RetryableErrorEvent


async def _gather_one_score(arxiv_id: str) -> Dict:
    url = f"https://api.altmetric.com/v1/arxiv/{arxiv_id}"

    # We use verify=False to avoid the SSLWantReadError error
    for _ in range(ALTMETRIC_N_RETRIES):
        try:
            async with httpx.AsyncClient(verify=False) as client:
                response = await client.get(url)
        except Exception as e:
            RetryableErrorEvent(
                msg=f"Error retrieving {arxiv_id} from altmetric at {url}",
                context={"exception": str(e)},
            )
            time.sleep(ALTMETRIC_WAIT_TIME)
            continue
        else:
            break
    else:
        response = None

    if response is not None and response.status_code == 200:
        js = response.json()

        # Let's use the cumulative score
        score = js["history"]["at"]

    else:
        # Probably not yet processed
        score = -1

    return {"arxiv": arxiv_id, "score": score}


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
        InfoEvent(
            msg=f"Fetching from Altmetric the scores for papers {i} - {i+chunk_size}"
        )
        chunk = arxiv_ids[i : i + chunk_size]
        chunk_results = await asyncio.gather(*[_gather_one_score(x) for x in chunk])
        results.extend(chunk_results)

        delay = random.randint(1, 5)
        InfoEvent(f"Waiting for {delay} seconds")
        time.sleep(delay)

    assert len(results) == len(arxiv_ids)

    return results
