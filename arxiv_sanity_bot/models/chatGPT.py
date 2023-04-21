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
    def summarize_abstract(self, abstract: str) -> str:
        summary = ""

        for i in range(CHATGPT_N_TRIALS):
            history = [
                {
                    "role": "system",
                    "content": f"You are a twitter chat bot. You can only answer with a maximum of "
                    f"{TWEET_TEXT_LENGTH} characters",
                },
                {
                    "role": "user",
                    "content": f"Summarize the following abstract in one short sentence: `{abstract}`. "
                    "Do not include any hashtag",
                },
            ]

            r = openai.ChatCompletion.create(
                model="gpt-3.5-turbo-0301",
                messages=history,
            )

            summary = r["choices"][0]["message"]["content"].strip()

            if len(summary) <= TWEET_TEXT_LENGTH:
                # This is a good tweet
                break
            else:
                RetryableErrorEvent(
                    msg=f"Summary was {len(summary)} characters long instead of {TWEET_TEXT_LENGTH}.",
                    context={"abstract": abstract, "this_summary": summary},
                )
        else:
            FatalErrorEvent(
                msg=f"ChatGPT could not successfully generate a tweet after {CHATGPT_N_TRIALS}",
                context={"abstract": abstract},
            )

        return summary

    def generate_bot_summary(self, n_papers_considered: int, n_papers_reported: int):
        # Generate a fun variation of the following phrase using ChatGPT
        sentence = (
            f"Hi! In this round I considered {n_papers_considered} papers and selected the "
            f"top {n_papers_reported}. One-sentence summaries in the thread."
        )

        for i in range(CHATGPT_N_TRIALS):
            history = [
                {"role": "system", "content": "You are a helpful assistant."},
                {
                    "role": "user",
                    "content": f"Generate an engaging variation of the following sentence, "
                               f"but avoid sounding too human (you are a bot!): "
                               f"{sentence}",
                },
            ]

            try:
                r = openai.ChatCompletion.create(
                    model="gpt-3.5-turbo-0301",
                    messages=history,
                )
            except openai.OpenAIError as e:
                RetryableErrorEvent(
                    msg="Could not generate summary sentence",
                    context={"exception": str(e)},
                )
                time.sleep(CHATGPT_SLEEP_TIME)
                continue
            else:
                sentence = r["choices"][0]["message"]["content"].strip()
                break

        return sentence
