#!/usr/bin/env bash

set -eu

CLOUD=$1
JOBID=$2

state=`python abm $CLOUD job show $JOBID | jq -r ".state"`
while [ $state = "running" ] ; do
    echo $state
    sleep 30
    state=`python abm $CLOUD job show $JOBID | jq -r ".state"`
done
python abm $CLOUD job show $JOBID | jq -r ".state"
echo "Done."