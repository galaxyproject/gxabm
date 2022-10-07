import os
import json
import logging

from pprint import pprint

import requests
import yaml
from planemo.runnable import for_path
from planemo.galaxy.workflows import install_shed_repos
from common import connect, Context
from pathlib import Path

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
    if path.startsWith('http'):
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


def import_from_url(context: Context, args:list):
    if len(args) == 0:
        print("ERROR: no workflow URL given")
        return
    url = args[0]
    response = requests.get(url)
    if (response.status_code != 200):
        print(f"ERROR: There was a problem downloading the workflow: {response.status_code}")
        print(response.reason)
        return
    try:
        workflow = json.loads(response.text)
    except Exception as e:
        print("ERROR: Unable to parse workflow")
        print(e)
        return

    gi = connect(context)
    result = gi.workflows.import_workflow_dict(workflow)
    print(json.dumps(result, indent=4))


def import_from_config(context: Context, args:list):
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
    import_from_url(context, [ url ])


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
    pprint(gi.workflows.show_workflow(args[0]))


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
        print("USAGE: publish ID" )
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


