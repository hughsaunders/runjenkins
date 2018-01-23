#!/bin/bash -xe
pylama --skip "*venv/*"
pytest test_runjenkins.py
