import os
import sys
import yaml
import json
from pprint import pprint
from planemo.runnable import for_path
from planemo.galaxy.workflows import install_shed_repos

from common import connect

INVOCATIONS_DIR = "invocations"

class Keys:
    NAME = 'name'
    RUNS = 'runs'
    INPUTS = 'inputs'
    REFERENCE_DATA = 'reference_data'
    WORKFLOW_ID = 'workflow_id'
    DATASET_ID = 'dataset_id'
    HISTORY_BASE_NAME = 'output_history_base_name'
    HISTORY_NAME = 'history_name'


def find_workflow_id(gi, name_or_id):
    try:
        wf = gi.workflows.show_workflow(name_or_id)
        return wf['id']
    except:
        pass

    try:
        wf = gi.workflows.get_workflows(name=name_or_id, published=True)
        return wf[0]['id']
    except:
        pass
    #print(f"Warning: unable to find workflow {name_or_id}")
    return None


def find_dataset_id(gi, name_or_id):
    # print(f"Finding dataset {name_or_id}")
    try:
        ds = gi.datasets.show_dataset(name_or_id)
        return ds['id']
    except:
        pass

    try:
        # print('Trying by name')
        ds = gi.datasets.get_datasets(name=name_or_id)  # , deleted=True, purged=True)
        if len(ds) > 0:
            return ds[0]['id']
    except:
        print('Caught an exception')
        print(sys.exc_info())
    print(f"Warning: unable to find dataset {name_or_id}")
    return name_or_id


def parse_workflow(workflow_path: str):
    if not os.path.exists(workflow_path):
        print(f'ERROR: could not find workflow file {workflow_path}')
        return None

    with open(workflow_path, 'r') as stream:
        try:
            config = yaml.safe_load(stream)
            # print(f"Loaded {name}")
        except yaml.YAMLError as exc:
            print('Error encountered parsing the YAML input file')
            print(exc)
            sys.exit(1)
    return config


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


def run(args: list):
    if len(args) == 0:
        print('ERROR: no workflow configuration specified')
        return
    workflow_path = args[0]
    if not os.path.exists(workflow_path):
        print(f'ERROR: can not find workflow configuration {workflow_path}')
        return

    if os.path.exists(INVOCATIONS_DIR):
        if not os.path.isdir(INVOCATIONS_DIR):
            print('ERROR: Can not save invocation status, directory name in use.')
            sys.exit(1)
    else:
        os.mkdir(INVOCATIONS_DIR)

    gi = connect()
    workflows = parse_workflow(workflow_path)
    # with open(workflow_path, 'r') as stream:
    #     try:
    #         config = yaml.safe_load(stream)
    #         print(f"Loaded {workflow_path}")
    #     except yaml.YAMLError as exc:
    #         print('Error encountered parsing the YAML input file')
    #         print(exc)
    #         sys.exit(1)

    print(f"Found {len(workflows)} workflow definitions")
    for workflow in workflows:
        wfid = workflow[Keys.WORKFLOW_ID]
        wfid = find_workflow_id(gi, wfid)
        if wfid is None:
            print(f"Unable to load the workflow ID for {workflow[Keys.WORKFLOW_ID]}")
            return
        else:
            print(f"Found workflow id {wfid}")
        inputs = {}
        history_base_name = wfid
        if Keys.HISTORY_BASE_NAME in workflow:
            history_base_name = workflow[Keys.HISTORY_BASE_NAME]

        if Keys.REFERENCE_DATA in workflow:
            for spec in workflow[Keys.REFERENCE_DATA]:
                input = gi.workflows.get_workflow_inputs(wfid, spec[Keys.NAME])
                if input is None or len(input) == 0:
                    print(f'ERROR: Invalid input specification for {spec[Keys.NAME]}')
                    sys.exit(1)
                dsid = find_dataset_id(gi, spec[Keys.DATASET_ID])
                print(f"Reference input dataset {dsid}")
                inputs[input[0]] = {'id': dsid, 'src': 'hda'}

        count = 0
        for run in workflow[Keys.RUNS]:
            count += 1
            if Keys.HISTORY_NAME in run:
                output_history_name = f"{history_base_name} {run[Keys.HISTORY_NAME]}"
            else:
                output_history_name = f"{history_base_name} run {count}"
            for spec in run[Keys.INPUTS]:
                input = gi.workflows.get_workflow_inputs(wfid, spec[Keys.NAME])
                if input is None or len(input) == 0:
                    print(f'ERROR: Invalid input specification for {spec[Keys.NAME]}')
                    sys.exit(1)
                dsid = find_dataset_id(gi, spec[Keys.DATASET_ID])
                print(f"Input dataset ID: {dsid}")
                inputs[input[0]] = {'id': dsid, 'src': 'hda'}

            invocation = gi.workflows.invoke_workflow(wfid, inputs=inputs, history_name=output_history_name)
            pprint(invocation)
            # output_path = os.path.join(INVOCATIONS_DIR, invocation['id'] + '.json')
            output_path = os.path.join(INVOCATIONS_DIR, output_history_name.replace(' ', '_') + '.json')
            with open(output_path, 'w') as f:
                json.dump(invocation, f, indent=4)
                print(f"Wrote {output_path}")


def test(args: list):
    gi = connect()
    print(f"Searching for workflow {args[0]}")
    flows = gi.workflows.get_workflows(name=args[0], published=True)
    pprint(flows)


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


def translate(args: list):
    if len(args) == 0:
        print('ERROR: no workflow configuration specified')
        return
    workflow_path = args[0]
    if not os.path.exists(workflow_path):
        print(f'ERROR: can not find workflow configuration {workflow_path}')
        return

    gi = connect()
    # wf_index,ds_index = create_rev_index(gi)
    workflows = parse_workflow(args[0])
    for workflow in workflows:
        wfid = workflow[Keys.WORKFLOW_ID]
        wfinfo = gi.workflows.show_workflow(wfid)
        if wfinfo is None or 'name' not in wfinfo:
            print(f"Warning: unable to translate workflow ID {wfid}")
        else:
            workflow[Keys.WORKFLOW_ID] = wfinfo['name']
        # if workflow[Keys.WORKFLOW_ID] in wf_index:
        #     workflow[Keys.WORKFLOW_ID] = wf_index[workflow[Keys.WORKFLOW_ID]]
        # else:
        #     print(f"Warning: no workflow id for {workflow[Keys.WORKFLOW_ID]}")
        if Keys.REFERENCE_DATA in workflow:
            for ref in workflow[Keys.REFERENCE_DATA]:
                dsid = ref[Keys.DATASET_ID]
                dataset = gi.datasets.show_dataset(dsid)
                if dataset is None:
                    print(f"Warning: could not translate dataset ID {dsid}")
                else:
                    ref[Keys.DATASET_ID] = dataset['name']
        for run in workflow[Keys.RUNS]:
            for input in run[Keys.INPUTS]:
                dsid = input[Keys.DATASET_ID]
                dataset = gi.datasets.show_dataset(dsid)
                if dataset is None:
                    print(f"Warning: could not translate dataset ID {dsid}")
                else:
                    input[Keys.DATASET_ID] = dataset['name']
    print(yaml.dump(workflows))


def validate(args: list):
    if len(args) == 0:
        print('ERROR: no workflow configuration specified')
        return

    workflow_path = args[0]
    if not os.path.exists(workflow_path):
        print(f'ERROR: can not find workflow configuration {workflow_path}')
        return
    workflows = parse_workflow(workflow_path)
    gi = connect()
    total_errors = 0
    for workflow in workflows:
        wfid = workflow[Keys.WORKFLOW_ID]
        try:
            wfid = find_workflow_id(gi, wfid)
        except:
            wfid = None

        if wfid is None:
            print(f"The workflow '{workflow[Keys.WORKFLOW_ID]}' does not exist on this server.")
            return
        else:
            print(f"Workflow: {workflow[Keys.WORKFLOW_ID]} -> {wfid}")
        inputs = {}
        errors = 0
        history_base_name = wfid
        if Keys.HISTORY_BASE_NAME in workflow:
            history_base_name = workflow[Keys.HISTORY_BASE_NAME]

        if Keys.REFERENCE_DATA in workflow:
            for spec in workflow[Keys.REFERENCE_DATA]:
                input = gi.workflows.get_workflow_inputs(wfid, spec[Keys.NAME])
                if input is None or len(input) == 0:
                    print(f'ERROR: Invalid input specification for {spec[Keys.NAME]}')
                    errors += 1
                    #sys.exit(1)
                else:
                    dsid = find_dataset_id(gi, spec[Keys.DATASET_ID])
                    print(f"Reference input dataset {spec[Keys.DATASET_ID]} -> {dsid}")
                    inputs[input[0]] = {'id': dsid, 'src': 'hda'}

        count = 0
        for run in workflow[Keys.RUNS]:
            count += 1
            for spec in run[Keys.INPUTS]:
                input = gi.workflows.get_workflow_inputs(wfid, spec[Keys.NAME])
                if input is None or len(input) == 0:
                    print(f'ERROR: Invalid input specification for {spec[Keys.NAME]}')
                    errors += 1
                else:
                    dsid = find_dataset_id(gi, spec[Keys.DATASET_ID])
                    print(f"Input dataset: {spec[Keys.DATASET_ID]} -> {dsid}")
                    inputs[input[0]] = {'id': dsid, 'src': 'hda'}

        if errors == 0:
            print("This workflow configuration is valid and can be executed on this server.")
        else:
            print("The above problems need to be corrected before this workflow configuration can be used.")
        total_errors += errors

    return total_errors == 0