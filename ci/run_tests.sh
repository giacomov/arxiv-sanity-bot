#!/bin/bash -e

uv sync --all-extras
uv run coverage run -m pytest -vv tests/
uv run coverage report
