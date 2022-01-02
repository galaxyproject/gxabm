import os
import sys
import yaml
import json
from pprint import pprint
from planemo.runnable import for_path
from planemo.galaxy.workflows import install_shed_repos
from lib import Keys
import common
from bioblend.galaxy import GalaxyInstance
from common import connect

def list(args: list):
    gi = connect()
    workflows = gi.workflows.get_workflows(published=True)
    if len(workflows) == 0:
        print('No workflows found')
        return
    print(f'Found {len(workflows)} workflows')
    for workflow in workflows:
        print(f"{workflow['id']}\t{workflow['name']}")


def delete(args: list):
    if len(args) == 0:
        print(f'ERROR: no workflow ID given.')
        return
    gi = connect()
    print(gi.workflows.delete_workflow(args[0]))


def upload(args: list):
    if len(args) == 0:
        print('ERROR: no workflow file given')
        return
    path = args[0]
    if not os.path.exists(path):
        print(f'ERROR: file not found: {path}')
        return
    gi = connect()
    print("Importing the workflow")
    pprint(gi.workflows.import_workflow_from_local_path(path, publish=True))
    runnable = for_path(path)
    print("Installing tools")
    result = install_shed_repos(runnable, gi, False)
    pprint(result)


def download(args: list):
    if len(args) == 0:
        print('ERROR: no workflow ID given')
        return
    gi = connect()
    workflow = json.dumps(gi.workflows.export_workflow_dict(args[0]), indent=4)
    if len(args) == 2:
        with open(args[1], 'w') as f:
            f.write(workflow)
            print(f'Wrote {args[1]}')
    else:
        print(workflow)


def show(args: list):
    if len(args) == 0:
        print('ERROR: no workflow ID given')
        return
    gi = connect()
    pprint(gi.workflows.show_workflow(args[0]))


def find(args: list):
    if len(args) == 0:
        print("ERROR: no workflow name given")
        return
    gi = connect()
    pprint(gi.workflows.get_workflows(name=args[0]))


def test(args: list):
    # gi = connect()
    # print(f"Searching for workflow {args[0]}")
    # flows = gi.workflows.get_workflows(name=args[0], published=True)
    # pprint(flows)
    print(__name__)

def publish(args: list):
    if len(args) != 1:
        print("USAGE: publish ID" )
        return
    gi = connect()
    result = gi.workflows.update_workflow(args[0], published=True)
    print(f"Published: {result['published']}")


def rename(args: list):
    if len(args) != 2:
        print("USAGE: rename ID 'new workflow name'")
        return
    gi = connect()
    result = gi.workflows.update_workflow(args[0], name=args[1])
    print(f"Renamed workflow to {result['name']}")


