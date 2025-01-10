# <img src="https://user-images.githubusercontent.com/5917371/231673318-afd0253d-a31a-4265-a44d-5334ed872408.png" width="50"> arxiv-sanity-bot

[![Run Arxiv Sanity Bot](https://github.com/giacomov/arxiv-sanity-bot/actions/workflows/run-arxiv-sanity-bot.yml/badge.svg)](https://github.com/giacomov/arxiv-sanity-bot/actions/workflows/run-arxiv-sanity-bot.yml)
[![Maintainability](https://api.codeclimate.com/v1/badges/bf7a3c98c285aa95f935/maintainability)](https://codeclimate.com/github/giacomov/arxiv-sanity-bot/maintainability)
[![Test Coverage](https://api.codeclimate.com/v1/badges/bf7a3c98c285aa95f935/test_coverage)](https://codeclimate.com/github/giacomov/arxiv-sanity-bot/test_coverage)

![Slide 2 (2)](https://user-images.githubusercontent.com/5917371/233284690-2a548958-4212-4e39-963d-ad6ae967b4b8.jpeg)

This repository contains the code for `arxiv-sanity-bot`, a system that:

1. takes the most recent AI/ML papers from [arxiv](https://arxiv.org)
2. ranks them by [Altmetric score](https://api.altmetric.com/docs/call_arxiv.html)
3. selects papers above a threshold
4. sends them to GPT-4o for summarization using the [OpenAI API](https://platform.openai.com/docs/introduction)
5. Extract the first image of the paper
6. posts the results to [X/Twitter](https://twitter.com/arxivsanitybot) using [tweepy](https://www.tweepy.org/)

Clicking on the shortened URL in the tweet takes you to the arxiv page.


## How it works

The code runs periodically as a [Github action](https://github.com/giacomov/arxiv-sanity-bot/blob/main/.github/workflows/run-arxiv-sanity-bot.yml) (so it runs on free compute here on Github). It fetches the last papers from [arxiv](https://arxiv.org), parses all the papers contained there extracting title, abstract and arxiv number, then sends the arxiv numbers to Altmetrics to collect the Altmetric score. After putting everything together in a pandas DataFrame, it sorts it by score, then sends the first results to GPT-4o for summarization using the OpenAI API. It then extracts the first image of the paper (if it exists). Each result is concatenated with a shortened version of its Arxiv link and then posted on X/Twitter, with the first image of the paper attached.


### Notes

* The icon for the bot was generated using Stable Diffusion
* In order to accumulate enough signal for the Altmetric score, the bot considers papers within a window going back a few days
* The bot avoids reposting the same paper multiple times by maintaining track of the posted tweets, exploiting a Firebase database (free quota).
* All parameters governing the functioning of the bot are contained in the [config.py](https://github.com/giacomov/arxiv-sanity-bot/blob/main/arxiv_sanity_bot/config.py) module.
