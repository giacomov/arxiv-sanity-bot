import json
import time

from arxiv_sanity_bot.events import RetryableErrorEvent, FatalErrorEvent
from arxiv_sanity_bot.models.model import LLM
from arxiv_sanity_bot.config import (
    CHATGPT_N_TRIALS,
    TWEET_TEXT_LENGTH,
    CHATGPT_SLEEP_TIME,
)
import openai


class ChatGPT(LLM):

    def __init__(self):
        self._client = openai.OpenAI()

    def summarize_abstract(self, abstract: str) -> str:
        summary = ""

        history = [
            {
                "role": "system",
                "content": f"You are a twitter chat bot. Write engaging tweets with a maximum length of "
                f"{TWEET_TEXT_LENGTH} characters. Be concise, informative, and engaging.",
            },
            {
                "role": "user",
                "content": f"Summarize the following abstract in one short tweet: `{abstract}`. "
                "Do not include any hashtag. Make sure to highlight the innovative contribution of the paper. "
                f"Use the third person when referring to the authors. Use {TWEET_TEXT_LENGTH} or less "
                "characters.",
            },
        ]

        for _ in range(CHATGPT_N_TRIALS):

            summary = self._call_chatgpt(history)

            if len(summary) <= TWEET_TEXT_LENGTH:
                # This is a good tweet
                break
            else:
                RetryableErrorEvent(
                    msg=f"Summary was {len(summary)} characters long instead of {TWEET_TEXT_LENGTH}.",
                    context={"abstract": abstract, "this_summary": summary},
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
            FatalErrorEvent(
                msg=f"ChatGPT could not successfully generate a tweet after {CHATGPT_N_TRIALS}",
                context={"abstract": abstract},
            )

        return summary

    def generate_bot_summary(
        self, n_papers_considered: int, n_papers_reported: int
    ):
        # Generate a fun variation of the following phrase using ChatGPT
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

        sentence = self._call_chatgpt(history)

        return sentence

    def _call_chatgpt(self, history):
        for i in range(CHATGPT_N_TRIALS):

            try:
                print(json.dumps(history, indent=4))

                completion = self._client.chat.completions.create(
                    model="gpt-4o",
                    messages=history,
                    max_completion_tokens=62,  # around 250 characters
                )
            except Exception as e:
                RetryableErrorEvent(
                    msg="Could not generate summary sentence",
                    context={"exception": str(e)},
                )
                time.sleep(CHATGPT_SLEEP_TIME)
                continue
            else:
                sentence = completion.choices[0].message.content.strip()
                return sentence

        else:

            FatalErrorEvent(
                msg=f"Calling ChatGPT failed after {CHATGPT_N_TRIALS} attempts"
            )
