import os
import time
from common import run, find_executable, Context


def update(context: Context, args:list):
    """
    Runs the ``helm upgrade`` command on the cluster to update the
    *jobs.rules.container_mapper_rules* configuration.

    :param args:  a list containing the path to the rules YAML file.  See the
      *running* directory for examples.
    :return:
    """
    if context.KUBECONFIG is None:
        print("ERROR: No kubeconfig is specified in the profile")
        return False

    if len(args) == 0:
        print("ERROR: No rules specified.")
        return False
    rules = args[0]

    helm = find_executable('helm')
    if helm is None:
        print('ERROR: helm is not available on the $PATH')
        return False

    if not os.path.exists(rules):
        print(f"ERROR: Rules file not found: {rules}")
        return False

    print(f"Applying rules {rules}")
    command = f"{helm} upgrade galaxy galaxy/galaxy -n galaxy --reuse-values --set-file jobs.rules.container_mapper_rules\.yml={rules}"
    try:
        result = run(command)
    except RuntimeError as e:
        print(e)
        return False

    if result is None:
        return False

    print('Waiting for the new deployments to come online')
    wait_until_ready()
    return True


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
        # TODO The namespace should be parameterized
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
            print(f'Pods: {len(pods)}')
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


def list(context: Context, args: list):
    print("Not implemented")

