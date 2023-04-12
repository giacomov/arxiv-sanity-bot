from arxiv_sanity_bot.events import RetryableErrorEvent, FatalErrorEvent
from arxiv_sanity_bot.models.model import LLM
from arxiv_sanity_bot.config import CHATGPT_N_TRIALS, TWEET_TEXT_LENGTH
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
                    context={
                        "abstract": abstract,
                        "this_summary": summary
                    }
                )
        else:

            FatalErrorEvent(
                msg=f"ChatGPT could not successfully generate a tweet after {CHATGPT_N_TRIALS}",
                context={
                    "abstract": abstract
                }
            )

        return summary
