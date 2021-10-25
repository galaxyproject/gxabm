#!/usr/bin/env bash

set -eu

LABEL=$1
TITLE=$2

PROJECT=Benchmarking

gh issue create --title "$TITLE" --label $LABEL --project $PROJECT
