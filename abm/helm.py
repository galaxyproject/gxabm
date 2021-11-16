import io
import os
import time
import common
from common import run, find_executable
import subprocess


def update(args:list):
    if common.KUBECONFIG is None:
        print("ERROR: No kubeconfig is specified in the profile")
        return

    if len(args) == 0:
        print("ERROR: No rules specified.")
        return
    rules = args[0]

    helm = find_executable('helm')
    if helm is None:
        print('ERROR: helm is not available on the $PATH')
        return

    rules_file = f"rules/rules_{rules}.yml"
    if not os.path.exists(rules_file):
        print(f"ERROR: Rules file not found: {rules_file}")
        return

    print(f"Applying rules {rules_file}")
    command = f"{helm} upgrade galaxy galaxy/galaxy -n galaxy --reuse-values --set-file jobs.rules.container_mapper_rules\.yml={rules_file}"
    # print(command)
    # print(run(f"{helm} repo update", {'KUBECONFIG': common.KUBECONFIG}))
    result = run(command)
    if result is not None:
        print(result)
        print('Waiting for the new deployments to come online')
        wait_until_ready()


def filter(lines:list, item:str):
    result = []
    for line in lines:
        if item in line:
            result.append(line)
    return result

def wait_for(kubectl:str, name: str):
    print(f"Waiting for {name} to be in the Running state")
    waiting = True
    while waiting:
        result = run(f"{kubectl} get pods -n galaxy")
        if result is None:
            waiting = False
            break
        lines = result.split('\n')
        pods = filter(lines, name)
        if len(pods) == 1:
            tokens = pods[0].split()
            waiting = tokens[2] != 'Running'
        if waiting:
            print(f'{len(pods)} zzz...')
            for pod in pods:
                print(pod)
            time.sleep(30)
    print(f"{name} is running")


def wait_until_ready():
    kubectl = find_executable('kubectl')
    if kubectl is None:
        print('ERROR: kubectl is not available on the $PATH')
        return
    wait_for(kubectl, 'galaxy-job')
    wait_for(kubectl, 'galaxy-web')
    wait_for(kubectl, 'galaxy-workflow')


def list(args: list):
    print("Not implemented")

