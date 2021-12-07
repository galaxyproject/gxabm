from .common import connect
import json
from pprint import pprint

def list(args: list):
    state = ''
    while len(args) > 0:
        arg = args.pop(0)
        if arg in ['-s', '--state', 'state']:
            if len(args) == 0:
                print("ERROR: specify a state, eg 'ok', 'error'")
                return
            state = args.pop(0)

    gi = connect()
    for job in gi.jobs.get_jobs(state=state):
        print(f"{job['id']}\t{job['state']}\t{job['update_time']}\t{job['tool_id']}")


def show(args: list):
    if len(args) != 1:
        print("ERROR: Invalid parameters. Job ID is required")
        return
    gi = connect()
    job = gi.jobs.show_job(args[0], full_details=True)
    print(json.dumps(job, indent=4))


def get_value(metric: dict):
    if metric['name'] == 'runtime_seconds':
        return metric['raw_value']
    return metric['value']


def metrics(args: list):
    if len(args) == 0:
        print("ERROR: no job ID provided")
        return
    gi = connect()
    #metrics = gi.jobs.get_metrics(args[0])
    metrics = {}
    for m in gi.jobs.get_metrics(args[0]):
        metrics[m['name']] = get_value(m)
    try:
        print(f"{metrics['galaxy_slots']},{metrics['galaxy_memory_mb']},{metrics['runtime_seconds']}")
    except:
        print(',,')
