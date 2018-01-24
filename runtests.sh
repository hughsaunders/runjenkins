#!/bin/bash -xe
if which travis; then
    travis lint -x .travis.yml
else
    echo "Skipping travis lint as travis command not available. "
    echo "On osx, install from brew, otherwise gem."
fi
bashate *.sh
pylama --skip "*venv/*"
pytest test_runjenkins.py
