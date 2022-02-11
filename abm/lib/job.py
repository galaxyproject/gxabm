import json
from .common import connect, Context
from pprint import pprint
import logging

log = logging.getLogger('abm')


def list(context: Context, args: list):
    state = ''
    log.debug('Processing args')
    log_state = False
    while len(args) > 0:
        arg = args.pop(0)
        if arg in ['-s', '--state', 'state']:
            if len(args) == 0:
                print("ERROR: specify a state, eg 'ok', 'error'")
                return
            state = args.pop(0)
            log_state = True

    log.debug('Connecting to the Galaxy server')
    gi = connect(context)
    if log_state:
        log.debug(f"Getting jobs with state {state}")
    else:
        log.debug("Getting job list")
    job_list = gi.jobs.get_jobs(state=state)
    log.debug(f"Iterating over job list with {len(job_list)} items")
    for job in job_list:
        print(f"{job['id']}\t{job['state']}\t{job['update_time']}\t{job['tool_id']}")


def show(context: Context, args: list):
    if len(args) != 1:
        print("ERROR: Invalid parameters. Job ID is required")
        return
    gi = connect(context)
    job = gi.jobs.show_job(args[0], full_details=True)
    print(json.dumps(job, indent=4))


def get_value(metric: dict):
    if metric['name'] == 'runtime_seconds':
        return metric['raw_value']
    return metric['value']


def metrics(context: Context, args: list):
    if len(args) == 0:
        print("ERROR: no job ID provided")
        return
    gi = connect(context)
    metrics = gi.jobs.get_metrics(args[0])
    print(json.dumps(metrics[0], indent=4))
    # metrics = {}
    # for m in gi.jobs.get_metrics(args[0]):
    #     metrics[m['name']] = get_value(m)
    # try:
    #     print(f"{metrics['galaxy_slots']},{metrics['galaxy_memory_mb']},{metrics['runtime_seconds']}")
    # except:
    #     print(',,')


def cancel(context: Context, args: list):
    if len(args) == 0:
        print('ERROR: no job ID provided.')
        return
    gi = connect(context)
    if gi.jobs.cancel_job(args[0]):
        print("Job canceled")
    else:
        print("ERROR: Unable to cancel job or job was already in a terminal state.")


def problems(context: Context, args: list):
    if len(args) == 0:
        print('ERROR: no job ID provided.')
        return
    gi = connect(context)
    pprint(gi.jobs.get_common_problems(args[0]))