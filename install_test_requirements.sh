#!/bin/bash -x

echo "Install Test Requirements"
pip install .
pip install -I -r test-requirements.txt
if which brew; then
    brew install travis
fi
