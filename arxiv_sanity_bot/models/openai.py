import json
import time
from typing import Any

from arxiv_sanity_bot.logger import get_logger, FatalError
from arxiv_sanity_bot.models.model import LLM
from arxiv_sanity_bot.config import (
    CHATGPT_N_TRIALS,
    TWEET_TEXT_LENGTH,
    CHATGPT_SLEEP_TIME,
)
import openai


logger = get_logger(__name__)


class OpenAI(LLM):

    def __init__(self):
        self._client = openai.OpenAI()

    def summarize_abstract(self, abstract: str) -> str:
        summary = ""

        history = [
            {
                "role": "system",
                "content": "You are a twitter chat bot. Write engaging tweets with a maximum length of "
                "255 characters. Be concise, informative, and engaging.",
            },
            {
                "role": "user",
                "content": f"Summarize the following abstract in one short tweet: `{abstract}`. "
                "Do not include any hashtag or emojis. Make sure to highlight the innovative contribution of the paper. "
                f"Use the third person when referring to the authors. Use 255 characters or less.",
            },
        ]

        for _ in range(CHATGPT_N_TRIALS):

            summary = self._call_openai(history)

            if len(summary) <= TWEET_TEXT_LENGTH:
                # This is a good tweet
                break
            else:
                logger.error(
                    f"Summary was {len(summary)} characters long instead of {TWEET_TEXT_LENGTH}.",
                    exc_info=True,
                    extra={"abstract": abstract, "this_summary": summary},
                )
                history.extend(
                    [
                        {"role": "assistant", "content": summary},
                        {
                            "role": "user",
                            "content": f"The tweet was too long ({len(summary)} characters). Make it a little shorter.",
                        },
                    ]
                )
        else:
            logger.critical(
                f"OpenAI could not successfully generate a tweet after {CHATGPT_N_TRIALS}",
                extra={"abstract": abstract},
            )
            raise FatalError(f"OpenAI could not successfully generate a tweet after {CHATGPT_N_TRIALS}")

        return summary

    def generate_bot_summary(
        self, n_papers_considered: int, n_papers_reported: int
    ) -> str:
        # Generate a fun variation of the following phrase using OpenAI
        original_sentence = (
            f"In this round I considered {n_papers_considered} abstracts and selected "
            f"{n_papers_reported}. Read the summaries in the following tweets. See you in a few hours!"
        )

        history = [
            {"role": "system", "content": "You are a helpful assistant."},
            {
                "role": "user",
                "content": f"Generate an engaging variation of the following sentence, "
                f"but avoid sounding too human (you are a bot!): "
                f"{original_sentence}",
            },
        ]

        sentence = self._call_openai(history)

        return sentence

    def _call_openai(self, history: list[dict[str, Any]]) -> str:
        for i in range(CHATGPT_N_TRIALS):

            try:
                print(json.dumps(history, indent=4))

                completion = self._client.chat.completions.create(
                    model="gpt-5-mini",
                    messages=history,
                )
            except Exception as e:
                logger.error(
                    "Could not generate summary sentence",
                    exc_info=True,
                    extra={"exception": str(e)},
                )
                time.sleep(CHATGPT_SLEEP_TIME)
                continue
            else:
                sentence = completion.choices[0].message.content.strip()
                return sentence

        logger.critical(f"Calling OpenAI failed after {CHATGPT_N_TRIALS} attempts")
        raise FatalError(f"Calling OpenAI failed after {CHATGPT_N_TRIALS} attempts")
