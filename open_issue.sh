#!/usr/bin/env bash

set -eu

LABEL=$1
TITLE=$2

PROJECT=ABM

gh issue create --title "$TITLE" --label $LABEL --project $PROJECT
