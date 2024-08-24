#!/usr/bin/env bash
set -e

rye build --clean
docker build -t tistaharahap/troy-python:latest .
docker push tistaharahap/troy-python:latest
