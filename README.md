# arxiv-sanity-bot
[![Run Arxiv Sanity Bot](https://github.com/giacomov/arxiv-sanity-bot/actions/workflows/run-arxiv-sanity-bot.yml/badge.svg)](https://github.com/giacomov/arxiv-sanity-bot/actions/workflows/run-arxiv-sanity-bot.yml)
[![Maintainability](https://api.codeclimate.com/v1/badges/bf7a3c98c285aa95f935/maintainability)](https://codeclimate.com/github/giacomov/arxiv-sanity-bot/maintainability)
[![Test Coverage](https://api.codeclimate.com/v1/badges/bf7a3c98c285aa95f935/test_coverage)](https://codeclimate.com/github/giacomov/arxiv-sanity-bot/test_coverage)

![Slide 2 (1)](https://user-images.githubusercontent.com/5917371/231667513-03886ce6-820a-4070-9609-fc914b88350b.jpeg)

This repository contains the code for `arxiv-sanity-bot`, a system that:
1. takes the most recent papers from [arxiv-sanity](https://arxiv-sanity-lite.com)
2. rank them by [Altmetric score](https://api.altmetric.com/docs/call_arxiv.html)
3. selects the 10 with the highest score
4. sends them to ChatGPT for summarization using the [OpenAI API](https://platform.openai.com/docs/introduction)
5. post the results to [Twitter](https://twitter.com/arxivsanitybot) using [tweepy](https://www.tweepy.org/)

If you don't use Twitter, you can also find the same tweets posted on [LinkedIn](https://www.linkedin.com/company/arxiv-sanity-bot/)
