import common
from common import run, find_executable


def pods(args: list):
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

