#!/bin/bash -xe
if which travis; then
    travis lint -x .travis.yml
else
    echo "Skipping travis lint as travis command not available. "
    echo "On osx, install from brew, otherwise gem."
fi
bashate *.sh
pylama --skip "*venv/*" --ignore C901
pytest test_runjenkins.py

if which pandoc; then
    pandoc -f markdown -t rst README.md > README.rst
    git add README.rst
else
    echo "skipping pandoc as not available"
fi
