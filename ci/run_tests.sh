#!/bin/bash -e

pip install ".[test]"
coverage run -m pytest -vv tests/
coverage report
