#!/bin/bash -e

pip install ".[test]"
coverage run -m pytest -vv -x tests/
coverage report
coverage xml
