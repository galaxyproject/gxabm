import json
import logging
import os
from pathlib import Path
from pprint import pprint

import planemo
import requests
import yaml
from common import Context, connect, summarize_metrics
from planemo.galaxy.workflows import install_shed_repos
from planemo.runnable import for_path, for_uri

log = logging.getLogger('abm')


def list(context: Context, args: list):
    gi = connect(context)
    workflows = gi.workflows.get_workflows(published=True)
    if len(workflows) == 0:
        print('No workflows found')
        return
    print(f'Found {len(workflows)} workflows')
    for workflow in workflows:
        print(f"{workflow['id']}\t{workflow['name']}")


def delete(context: Context, args: list):
    if len(args) == 0:
        print(f'ERROR: no workflow ID given.')
        return
    gi = connect(context)
    print(gi.workflows.delete_workflow(args[0]))


def upload(context: Context, args: list):
    if len(args) == 0:
        print('ERROR: no workflow file given')
        return
    path = args[0]
    if path.startswith('http'):
        import_from_url(context, args)
        return
    if not os.path.exists(path):
        print(f'ERROR: file not found: {path}')
        return
    gi = connect(context)
    print("Importing the workflow")
    pprint(gi.workflows.import_workflow_from_local_path(path, publish=True))
    runnable = for_path(path)
    print("Installing tools")
    result = install_shed_repos(runnable, gi, False)
    pprint(result)


def import_from_url(context: Context, args: list):
    if len(args) == 0:
        print("ERROR: no workflow URL given")
        return
    url = args[0]

    # There is a bug in ephemeris (for lack of a better term) that assumes all
    # Runnable objects can be found on the local file system
    input_text = None
    filename = url.split('/')[-1]
    cache = os.path.expanduser("~/.abm/cache/workflows")
    if not os.path.exists(cache):
        os.makedirs(cache)
    cached_file = os.path.join(cache, filename)
    if os.path.exists(cached_file):
        with open(cached_file) as f:
            input_text = f.read()
    else:
        response = requests.get(url)
        if response.status_code != 200:
            print(
                f"ERROR: There was a problem downloading the workflow: {response.status_code}"
            )
            print(response.reason)
            return
        input_text = response.text
        with open(cached_file, 'w') as f:
            f.write(input_text)

    # response = requests.get(url)
    # if (response.status_code != 200):
    #     print(f"ERROR: There was a problem downloading the workflow: {response.status_code}")
    #     print(response.reason)
    #     return
    try:
        workflow = json.loads(input_text)
    except Exception as e:
        print("ERROR: Unable to parse workflow")
        print(e)
        return

    gi = connect(context)
    result = gi.workflows.import_workflow_dict(workflow, publish=True)
    print(json.dumps(result, indent=4))
    runnable = for_path(cached_file)
    # runnable = for_uri(url)
    print("Installing tools")
    result = install_shed_repos(runnable, gi, False, install_tool_dependencies=True)
    pprint(result)


def import_from_config(context: Context, args: list):
    if len(args) == 0:
        print("ERROR: no workflow ID given")
        return
    key = args[0]
    userfile = os.path.join(Path.home(), ".abm", "workflows.yml")
    if not os.path.exists(userfile):
        print("ERROR: this instance has not been configured to import workflows.")
        print(f"Please configure {userfile} to enable workflow imports")
        return
    with open(userfile, 'r') as f:
        workflows = yaml.safe_load(f)
    if not key in workflows:
        print(f"ERROR: no such workflow: {key}")
        return

    url = workflows[key]
    import_from_url(context, [url])


def download(context: Context, args: list):
    if len(args) == 0:
        print('ERROR: no workflow ID given')
        return
    gi = connect(context)
    workflow = json.dumps(gi.workflows.export_workflow_dict(args[0]), indent=4)
    if len(args) == 2:
        with open(args[1], 'w') as f:
            f.write(workflow)
            print(f'Wrote {args[1]}')
    else:
        print(workflow)


def show(context: Context, args: list):
    if len(args) == 0:
        print('ERROR: no workflow ID given')
        return
    gi = connect(context)
    result = gi.workflows.show_workflow(args[0])
    print(json.dumps(result, indent=4))


def inputs(context: Context, args: list):
    if len(args) == 0:
        print('ERROR: no workflow ID given')
        return
    gi = connect(context)
    workflow = gi.workflows.show_workflow(args[0])
    inputs = workflow['inputs']
    for input_name, input_dict in inputs.items():
        print(input_name)
        print(json.dumps(input_dict, indent=4))


def invocation(context: Context, args: list):
    if len(args) != 2:
        print("ERROR: Invalid paramaeters. A workflow ID invocation ID are required")
        return
    workflow_id = None
    invocation_id = None
    while len(args) > 0:
        arg = args.pop(0)
        if arg in ['-w', '--work', '--workflow']:
            print("Setting workflow id")
            workflow_id = args.pop(0)
        # elif arg in ['-i', '--invoke', '--invocation']:
        #     invocation_id = args.pop(0)
        #     print("Setting invocation id")
        else:
            print(f'Invalid parameter: "{arg}')
            return
    if workflow_id is None:
        print("ERROR: No workflow ID provided")
        return
    # if invocation_id is None:
    #     print("ERROR: No invocation ID provided")
    #     return
    gi = connect(context)
    # result = gi.workflows.show_invocation(workflow_id, invocation_id)
    invocations = gi.invocations.get_invocations(
        workflow_id=workflow_id, view='element', step_details=True
    )
    # print(json.dumps(result, indent=4))
    print('ID\tState\tWorkflow\tHistory')
    for invocation in invocations:
        id = invocation['id']
        state = invocation['state']
        workflow = invocation['workflow_id']
        history = invocation['history_id']
        print(f'{id}\t{state}\t{workflow}\t{history}')


def find(context: Context, args: list):
    if len(args) == 0:
        print("ERROR: no workflow name given")
        return
    gi = connect(context)
    pprint(gi.workflows.get_workflows(name=args[0]))


def test(context: Context, args: list):
    # gi = connect(context)
    # print(f"Searching for workflow {args[0]}")
    # flows = gi.workflows.get_workflows(name=args[0], published=True)
    # pprint(flows)
    log.debug('debug')
    log.info('info')
    log.warning('warn')
    log.error('error')
    log.critical('critical')


def publish(context: Context, args: list):
    if len(args) != 1:
        print("USAGE: publish ID")
        return
    gi = connect(context)
    result = gi.workflows.update_workflow(args[0], published=True)
    print(f"Published: {result['published']}")


def rename(context: Context, args: list):
    if len(args) != 2:
        print("USAGE: rename ID 'new workflow name'")
        return
    gi = connect(context)
    result = gi.workflows.update_workflow(args[0], name=args[1])
    print(f"Renamed workflow to {result['name']}")


def summarize(context: Context, args: list):
    if len(args) == 0:
        print("ERROR: Provide one or more workflow ID values.")
        return
    gi = connect(context)
    wid = args[0]
    all_jobs = []
    invocations = gi.invocations.get_invocations(workflow_id=wid)
    for invocation in invocations:
        id = invocation['id']
        jobs = gi.jobs.get_jobs(invocation_id=id, workflow_id=wid)
        for job in jobs:
            job['invocation_id'] = id
            job['workflow_id'] = wid
            all_jobs.append(job)
    summarize_metrics(gi, all_jobs)
