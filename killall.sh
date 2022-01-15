#!/usr/bin/env bash

if [[ $# < 2 ]] ; then
    echo "USAGE  : $0 cloud state [state...]"
    echo "EXAMPLE: $0 tacc queued new"
    exit
fi

set -eu

cloud=$1
shift

while [[ $# > 0 ]] ; do
    state=$1
    shift
    for job in $(python abm.py $cloud job list --state $state | cut -f1) ; do
        echo "Killing job $job in state \"$state\""
        python abm.py $cloud job kill $job
    done
done