import json
from pprint import pprint

from common import Context, find_executable, get_env, run


def pods(context: Context, args: list):
    namespace = '-n galaxy'
    if len(args) > 0:
        if args[0] == 'all':
            namespace = '-A'
        else:
            namespace = f"-n {args[0]}"

    kubectl = find_executable('kubectl')
    if kubectl is None:
        print("ERROR: kubectl is not on the $PATH")
        return

    print(run(f"{kubectl} get pods {namespace}"))


def url(context: Context, args: list):
    print(get_url(context, args))


def get_url(context: Context, args: list):
    # pprint(context.__dict__)
    # return
    kubectl = find_executable('kubectl')
    if kubectl is None:
        print("ERROR: kubectl is not on the $PATH")
        return

    namespace = 'galaxy'
    name = 'galaxy'
    if len(args) > 0:
        namespace = args[0]
    if len(args) > 1:
        name = args[1]
    command = f"{kubectl} get svc -n {namespace} {name}-nginx -o json"
    result = run(command, get_env(context))
    data = json.loads(result)
    ports = data['spec']['ports'][0]
    protocol = ports['name']
    port = ports['port']
    ip = data['status']['loadBalancer']['ingress'][0]['ip']
    return f"{protocol}://{ip}:{port}/{name}/"
