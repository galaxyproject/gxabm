import argparse
import json
import os
import time

from common import Context, find_executable, get_env, run


def rollback(context: Context, args: list):
    helm = find_executable('helm')
    # helm = 'helm'
    if helm is None:
        print('ERROR: helm is not available on the $PATH')
        return

    print(
        f"Rolling back deployment on {context.GALAXY_SERVER} KUBECONFIG: {context.KUBECONFIG}"
    )
    if len(args) > 0:
        command = f"{helm} rollback " + ' '.join(args)
    else:
        command = f"{helm} rollback galaxy -n galaxy"
    run(command, get_env(context))


def update(context: Context, args: list):
    if len(args) == 0:
        print(f'USAGE: abm <cloud> helm update <values> <namespace> <chart>')
        return
    values = args[0]
    namespace = 'galaxy' if args[1] is None else args[1]
    chart = 'galaxy/galaxy' if args[2] is None else args[2]

    helm = find_executable('helm')
    if helm is None:
        print('ERROR: helm is not available on the $PATH')
        return False

    if not os.path.exists(values):
        print(f"ERROR: Rules file not found: {values}")
        return False

    print(f"Applying rules {values} to {context.GALAXY_SERVER}")
    print(f"Helm update namespace: {namespace}")
    print(f"Helm update chart: {chart}")
    # command = f'{helm} upgrade galaxy {chart} -n {namespace} --reuse-values --set-file jobs.rules."container_mapper_rules\.yml".content={rules}'
    command = f'{helm} upgrade galaxy {chart} -n {namespace} --reuse-values -f {values}'
    env = get_env(context)
    try:
        result = run(command, env)
    except RuntimeError as e:
        print(f"Unable to helm upgrade {context.GALAXY_SERVER}")
        print(e)
        return False

    if result is None:
        return False

    print('Waiting for the new deployments to come online')
    # Give kubernetes a moment to start processing the update.
    time.sleep(5)
    wait_until_ready(namespace)
    return True


def update_cli(context: Context, args: list):
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

    parser = argparse.ArgumentParser()
    parser.add_argument('-f', '--values')
    parser.add_argument('-n', '--namespace', default='galaxy')
    parser.add_argument('chart', default='galaxy/galaxy')

    params = parser.parse_args(args)
    update(context, [params.values, params.namespace, params.chart])


def wait(context: Context, args: list):
    namespace = args[0] if len(args) > 0 else 'galaxy'
    wait_until_ready(namespace)  # , get_env(context))


def filter(lines: list, item: str):
    result = []
    for line in lines:
        if item in line:
            result.append(line)
    return result


def wait_for(kubectl: str, namespace: str, name: str, env: dict):
    print(f"Waiting for {name} on {env['GALAXY_SERVER']} to be in the Running state")
    waiting = True
    while waiting:
        # TODO The namespace should be parameterized
        result = run(f"{kubectl} get pods -n {namespace}", env)
        if result is None:
            break
        lines = result.split('\n')
        pods = filter(lines, name)
        if len(pods) == 0:
            print(f"ERROR: there are no pods named {name} in namespace {namespace}")
        if len(pods) == 1:
            tokens = pods[0].split()
            waiting = tokens[2] != 'Running'
        if waiting:
            print(f'Pods: {len(pods)}')
            for pod in pods:
                print(pod)
            time.sleep(30)
    print(f"{name} is running")


# def wait_until_ready(namespace: str, env: dict):
#     kubectl = find_executable('kubectl')
#     if kubectl is None:
#         print('ERROR: kubectl is not available on the $PATH')
#         return
#     wait_for(kubectl, namespace, 'galaxy-job', env)
#     wait_for(kubectl, namespace, 'galaxy-web', env)
#     wait_for(kubectl, namespace, 'galaxy-workflow', env)
def wait_until_ready(namespace: str):
    kubectl = find_executable('kubectl')
    data = run(f"{kubectl} get deployment -n {namespace} -o json")
    deployment_data = json.loads(data)
    deployments = list()
    for deployment in deployment_data['items']:
        metadata = deployment['metadata']
        name = metadata['name']
        if 'job' in name or 'web' in name or 'workflow' in name:
            deployments.append(name)
    for deployment in deployments:
        print(
            run(
                f"{kubectl} rollout status deployment -n {namespace} {deployment} --watch"
            )
        )


def _list(context: Context, args: list):
    print("Not implemented")
