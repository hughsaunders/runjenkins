#!/bin/bash -x

echo "Install Test Requirements"
pip install .
pip install -r test-requirements.txt
