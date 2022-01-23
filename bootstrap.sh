#!/usr/bin/env bash
set -eu

#if [[ ! $(alias | grep abm) ]] ; then
#    source setup.sh
#fi
#alias
#abm help
#alias abm="python3 abm.py"
source .venv/bin/activate

while [[ $# > 0 ]] ; do
    cloud=$1
    shift
    echo "Bootstraping $cloud"
    python3 abm.py $cloud wf upload workflows/dna-cloud-costs.ga
    python3 abm.py $cloud history import dna
    python3 abm.py $cloud history import rna
done
