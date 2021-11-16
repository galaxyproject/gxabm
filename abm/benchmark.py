import io
import os
import sys
import yaml
import subprocess
from pprint import pprint

import common

def run(args: list):
    if len(args) == 0:
        print("ERROR: No configuration proviced")
        return
    if not os.path.exists(args[0]):
        print(f"ERROR: File not found: {args[0]}")
        return

    with open(args[0], "r") as f:
        benchmarks = yaml.safe_load(f)

    pprint(benchmarks)


def test(args: list):
    if common.KUBECONFIG is None:
        print("ERROR: No kubeconfig is specified in the profile")
        return

    # result = subprocess.run('/usr/local/bin/helm repo list'.split(' '), capture_output=True)
    kubectl = find_executable('kubectl')
    if kubectl is None:
        print('ERROR: kubectl is not available on the $PATH')
        return

    result = run(f"{kubectl} get pods -n galaxy", {'KUBECONFIG': common.KUBECONFIG})
    if result is not None:
        print(result)


