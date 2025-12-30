# <img src="https://user-images.githubusercontent.com/5917371/231673318-afd0253d-a31a-4265-a44d-5334ed872408.png" width="50"> arxiv-sanity-bot

[![Run Arxiv Sanity Bot](https://github.com/giacomov/arxiv-sanity-bot/actions/workflows/run-arxiv-sanity-bot.yml/badge.svg)](https://github.com/giacomov/arxiv-sanity-bot/actions/workflows/run-arxiv-sanity-bot.yml)
[![CI](https://github.com/giacomov/arxiv-sanity-bot/actions/workflows/run_tests.yml/badge.svg)](https://github.com/giacomov/arxiv-sanity-bot/actions/workflows/run_tests.yml)
[![Maintainability](https://qlty.sh/gh/giacomov/projects/arxiv-sanity-bot/maintainability.svg)](https://qlty.sh/gh/giacomov/projects/arxiv-sanity-bot)

This repository contains the code for `arxiv-sanity-bot`, a system that:

1. ranks the most recent AI/ML papers by combining multiple sources (as of today, AlphaXiv and Huggingface Papers)
2. selects top-ranked papers (papers appearing in both sources get priority)
3. sends them to OpenAI for summarization using the [OpenAI API](https://platform.openai.com/docs/introduction)
4. Extract the first image of the paper
5. posts the results to [X/Twitter](https://twitter.com/arxivsanitybot) using [tweepy](https://www.tweepy.org/)

Clicking on the shortened URL in the tweet takes you to the arxiv page.


## How it works

The code runs periodically as a [Github action](https://github.com/giacomov/arxiv-sanity-bot/blob/main/.github/workflows/run-arxiv-sanity-bot.yml) (so it runs on free compute here on Github). It fetches trending papers from [alphaXiv](https://alphaxiv.org) and daily papers from [HuggingFace](https://huggingface.co), combining them with a scoring system (2 points if a paper appears in both sources, 1 point otherwise). Papers are sorted by score and then by average rank. The top papers are sent to OpenAI for summarization using the OpenAI API. It then extracts the first image of the paper (if it exists). Each result is then posted on X/Twitter, with the first image of the paper attached.


### Notes

* The icon for the bot was generated using Stable Diffusion
* The bot considers papers within a time window going back a few days to ensure adequate trending signal
* The bot avoids reposting the same paper multiple times by maintaining track of the posted tweets, exploiting a Firebase database (free quota).
* All parameters governing the functioning of the bot are contained in the [config.py](https://github.com/giacomov/arxiv-sanity-bot/blob/main/arxiv_sanity_bot/config.py) module.
* **Note:** The bot previously used Altmetric scores, which was deprecated in 2024 when their API closed. The current ranking system uses alphaXiv + HuggingFace.
