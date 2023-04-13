# arxiv-sanity-bot
[![Run Arxiv Sanity Bot](https://github.com/giacomov/arxiv-sanity-bot/actions/workflows/run-arxiv-sanity-bot.yml/badge.svg)](https://github.com/giacomov/arxiv-sanity-bot/actions/workflows/run-arxiv-sanity-bot.yml)
[![Maintainability](https://api.codeclimate.com/v1/badges/bf7a3c98c285aa95f935/maintainability)](https://codeclimate.com/github/giacomov/arxiv-sanity-bot/maintainability)
[![Test Coverage](https://api.codeclimate.com/v1/badges/bf7a3c98c285aa95f935/test_coverage)](https://codeclimate.com/github/giacomov/arxiv-sanity-bot/test_coverage)

![Slide 2 (1)](https://user-images.githubusercontent.com/5917371/231667513-03886ce6-820a-4070-9609-fc914b88350b.jpeg)

This repository contains the code for `arxiv-sanity-bot`, a system that:

1. takes the most recent papers from [arxiv-sanity](https://arxiv-sanity-lite.com)
2. ranks them by [Altmetric score](https://api.altmetric.com/docs/call_arxiv.html)
3. selects the 10 with the highest score
4. sends them to ChatGPT for summarization using the [OpenAI API](https://platform.openai.com/docs/introduction)
5. posts the results to [Twitter](https://twitter.com/arxivsanitybot) using [tweepy](https://www.tweepy.org/)

Clicking on the shortened URL in the tweet takes you to the arxiv-sanity page, that lists not only the abstract and the link to that paper, but also all similar papers.

If you don't use Twitter, you can also find the same tweets posted on [LinkedIn](https://www.linkedin.com/company/arxiv-sanity-bot/)


## How it works

The code runs periodically as a [Github action](https://github.com/giacomov/arxiv-sanity-bot/blob/main/.github/workflows/run-arxiv-sanity-bot.yml) (so it runs on free compute here on Github). It fetches the last few pages from [arxiv-sanity](https://arxiv-sanity-lite.com), parses all the papers contained there extracting title, abstract and arxiv number, then sends the arxiv numbers to Altmetrics to collect the Altmetric score. After putting everything together in a pandas DataFrame, it sorts it by score, then sends the first results to ChatGPT for summarization using the OpenAI API. Each result is concatenated with a shortened version of its Arxiv-sanity link and then posted on Twitter.

An automation set up on [Zapier](https://zapier.com/) takes each tweet and reposts it on LinkedIN.

All parameters governing the functioning of the bot are contained in the [config.py](https://github.com/giacomov/arxiv-sanity-bot/blob/main/arxiv_sanity_bot/config.py) module.
