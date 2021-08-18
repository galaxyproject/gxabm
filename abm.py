#!/usr/bin/env python3

"""
The Automated Benchmarking Tool

Copyright 2021 The Galaxy Project. All rights reserved.

"""

import bioblend.galaxy
import yaml
import json
import sys
import os

from pprint import pprint

VERSION='0.1.0'

BOLD = '\033[1m'
CLEAR = '\033[0m'

# Default value for the Galaxy server URL.  This can be overriden with an
# environment variable or on the command line
GALAXY_SERVER = None #'https://benchmarking.usegvl.org/initial/galaxy/'

# Your Galaxy API key.  This can be specified in an environment variable or
# on the command line.
API_KEY = None

PROFILE_SEARCH_PATH = ['~/.abm/profile.yml', '.abm-profile.yml']
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

def bold(text:str):
    """
    Wraps the text in ANSI control sequences to generate bold text in the terminal.

    :param text: the text to be made bold
    :type str:
    :return: the original string wrapped in ANSI control sequences
    """
    return f"{BOLD}{text}{CLEAR}"


#
# Help functions
#
def help():
    program = sys.argv[0]
    print (f"""
{bold('SYNOPSIS')}
    Upload workflows and dataset to a Galaxy instance.
    
{bold('USAGE')}
    {program} COMMAND SUB-COMMAND [OPTIONS]
    
{bold('COMMANDS')}
    {bold('workflow')}|{bold('wf')}
        manage workflows on the Galaxy instance
    {bold('dataset')}|{bold('ds')}
        manage datasets on the Galaxy instance
    {bold('history')}|{bold('hist')}
        manage histories on the Galaxy instance
                
{bold('SUB-COMMANDS')}
    Most of the above commands support at least the following sub-commands.  
    Run {bold('./abm.py COMMAND help')} for a full list of the sub-commands supported
    
    {bold('list')}|{bold('ls')}
        list the workflows, datasets, or histories available on the Galaxy instance
    {bold('download')}|{bold('dl')} <name_or_id>
        downloads a workflow, dataset, or history from the Galaxy instance.
    {bold('upload')}|{bold('up')}
        uploads a workflow, dataset, or history from the Galaxy instance.
            
{bold('OPTIONS')}
    All command support the following options
    
    {bold('-k')}|{bold('--key')} APIKEY
        specify your API key for the Galaxy server
    {bold('-s')}|{bold('--server')} URL
        specify the URL of the Galaxy server
    {bold('-p')}|{bold('--profile')} PROFILE
        specify the file containing the API key and URL for the Galaxy server

Copyright 2021 The Galaxy Project. All rights reserved.    
""")

def workflow_help(args: list):
    program = sys.argv[0]
    print(f"""
    {bold('SYNOPSIS')}
        Manage workflows on a Galaxy instance.

    {bold('USAGE')}
        {program} workflow [list|upload|download|help] [OPTIONS]

    {bold('COMMANDS')}
        {bold('list')}|{bold('ls')}
            list the workflows available on the Galaxy instance
        {bold('download')}|{bold('down')}|{bold('dl')} ID <path>
            downloads a workflow from the Galaxy instance. If the <path> is given then
            workflow with be saved to that path.  Any existing file at that location will
            be overwritten.                    
        {bold('upload')}|{bold('up')} PATH
            uploads a workflow to the Galaxy instance.
                                        
    {bold('EXAMPLES')}
        {program} workflow ls
        {program} wf dl 5683bc67af /home/user/workflows/workflow.ga
        {program} wf upload /home/user/workflows/workflow.ga

    Copyright 2021 The Galaxy Project. All rights reserved.    
    """)


def history_help(args: list):
    program = sys.argv[0]
    print(f"""
    {bold('SYNOPSIS')}
        Manage histories on a Galaxy instance.

    {bold('USAGE')}
        {program} history [list|upload|download|help] [OPTIONS]

    {bold('COMMANDS')}
        {bold('list')}|{bold('ls')}
            list the histories available on the Galaxy instance
        {bold('download')}|{bold('down')}|{bold('dl')} ID PATH
            downloads a history from the Galaxy instance and saves to the path.  
            Any existing file at that location will be overwritten.                    
        {bold('upload')}|{bold('up')} PATH [NAME]
            uploads a dataset to the Galaxy instance. If the NAME is provided the
            dataset will be uploaded to a history with that name.  If the history
            does not exist it will be created.
            

    {bold('EXAMPLES')}
        {program} workflow ls
        {program} wf dl 5683bc67af /home/user/workflows/workflow.ga
        {program} wf upload /home/user/workflows/workflow.ga

    Copyright 2021 The Galaxy Project. All rights reserved.    
    """)


def library_help(args: list):
    program = sys.argv[0]
    print(f"""
    {bold('SYNOPSIS')}
        Manage dataset libraries on a Galaxy instance.

    {bold('USAGE')}
        {program} library [list|show|delete|upload] [OPTIONS]

    {bold('COMMANDS')}

    {bold('OPTIONS')}

    {bold('EXAMPLES')}


    Copyright 2021 The Galaxy Project. All rights reserved.    
    """)


def dataset_help(args: list):
    program = sys.argv[0]
    print(f"""
    {bold('SYNOPSIS')}
        Manage datasets on a Galaxy instance.

    {bold('USAGE')}
        {program} dataset [list|upload|download] [OPTIONS]

    {bold('COMMANDS')}
        {bold('list')}|{bold('ls')}
            list the histories available on the Galaxy instance
        {bold('download')}|{bold('down')}|{bold('dl')} ID PATH
            downloads a history from the Galaxy instance and saves to the path.  
            Any existing file at that location will be overwritten.                    
        {bold('upload')}|{bold('up')} PATH [NAME]
            uploads a dataset to the Galaxy instance. If the NAME is provided the
            dataset will be uploaded to a history with that name.  If the history
            does not exist it will be created.

    {bold('OPTIONS')}

    {bold('EXAMPLES')}


    Copyright 2021 The Galaxy Project. All rights reserved.    
    """)

def connect():
    """
    Create a connection to the Galaxy instance

    :return: a GalaxyInstance object
    """
    global GALAXY_SERVER, API_KEY
    if GALAXY_SERVER is None:
        print('ERROR: The Galaxy server URL has not been set.  You must either:')
        print('  1. Configure a profile and put it in ~/.abm/profile.yml')
        print('  2. Set the environment variable GALAXY_SERVER, or')
        print('  3. Pass the server URL with the -s|--server option')
        sys.exit(1)
    if API_KEY is None:
        print('ERROR: The Galaxy API key has not been set.  You must either:')
        print('  1. Configure a profile and put it in ~/.abm/profile.yml')
        print('  2. Set the environment variable API_KEY, or')
        print('  3. Pass the APi key with the -k|--key option')
        sys.exit(1)
    return bioblend.galaxy.GalaxyInstance(url=GALAXY_SERVER, key=API_KEY)


#
# Workflow related functions
#

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

def ignored(config):
    gi = connect()
    print(f"Connected to {GALAXY_SERVER}")
    print(f"Found {len(config)} workflow definitions")
    for workflow in config:
        wfid = workflow['workflow_id']
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
                inputs[input[0]] = { 'id': spec[Keys.DATASET_ID], 'src':'hda'}

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

                inputs[input[0]] = {'id': spec[Keys.DATASET_ID], 'src' : 'hda' }

            invocation = gi.workflows.invoke_workflow(wfid, inputs=inputs, history_name=output_history_name)
            pprint(invocation)
            # output_path = os.path.join(INVOCATIONS_DIR, invocation['id'] + '.json')
            # output_path = os.path.join(INVOCATIONS_DIR, output_history_name.replace(' ', '_') + '.json')
            # with open(output_path, 'w') as f:
            #     json.dump(invocation, f, indent=4)
            #     print(f"Wrote {output_path}")


def workflow_list(args: list):
    gi = connect()
    workflows = gi.workflows.get_workflows(published=True)
    if len(workflows) == 0:
        print('No workflows found')
        return
    print(f'Found {len(workflows)} workflows')
    for workflow in workflows:
        print(f"{workflow['id']}\t{workflow['name']}")

def workflow_delete(args:list):
    if len(args) == 0:
        print(f'ERROR: no workflow ID given.')
        return
    gi = connect()
    print(gi.workflows.delete_workflow(args[0]))

def workflow_upload(args:list):
    if len(args) == 0:
        print('ERROR: no workflow file given')
        return
    path = args[0]
    if not os.path.exists(path):
        print(f'ERROR: file not found: {path}')
        return
    gi = connect()
    pprint(gi.workflows.import_workflow_from_local_path(path, publish=True))

def workflow_download(args:list):
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

def workflow_show(args:list):
    if len(args) == 0:
        print('ERROR: no workflow ID given')
        return
    gi = connect()
    pprint(gi.workflows.show_workflow(args[0]))

def create_rev_index(gi):
    wfindex = dict()
    for workflow in gi.workflows.get_workflows(published=True):
        # pprint(workflow)
        # wfindex[workflow[Keys.NAME]] = workflow['id']
        wfindex[workflow['id']] = workflow[Keys.NAME]
        print(f"Index workflow {workflow['id']} ")
    # index['workflow'] = wfindex
    dsindex = dict()
    for dataset in gi.datasets.get_datasets(limit=1000, deleted=True, purged=False, ):
        # dsindex[dataset[Keys.NAME]] = dataset['id']
        dsindex[dataset['id']] = dataset[Keys.NAME]
        print(f"index dataset {dataset['id']}")
    # index['dataset'] = dsindex
    return wfindex, dsindex

def create_index(gi):
    wfindex = dict()
    for workflow in gi.workflows.get_workflows(published=True):
        # pprint(workflow)
        wfindex[workflow[Keys.NAME]] = workflow['id']
        print(f"Index {workflow[Keys.NAME]} = {workflow['id']}")
    # index['workflow'] = wfindex
    dsindex = dict()
    for dataset in gi.datasets.get_datasets(limit=1000, deleted=False, purged=False):
        dsindex[dataset[Keys.NAME]] = dataset['id']
    # index['dataset'] = dsindex
    return wfindex, dsindex

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
        print('Caught an exception')
        print(sys.exc_info())
        pass
    print(f"Warning: unable to find workflow {name_or_id}")
    return None


def find_dataset_id(gi, name_or_id):
    print(f"Finding dataset {name_or_id}")
    try:
        ds = gi.datasets.show_dataset(name_or_id)
        return ds['id']
    except:
        pass

    try:
        print('Trying by name')
        ds = gi.datasets.get_datasets(name=name_or_id) #, deleted=True, purged=True)
        if len(ds) > 0:
            return ds[0]['id']
    except:
        print('Caught an exception')
        print(sys.exc_info())
        pass
    print(f"Warning: unable to find dataset {name_or_id}")
    return name_or_id

def workflow_test(args: list):
    gi = connect()
    print(f"Searching for workflow {args[0]}")
    flows = gi.workflows.get_workflows(name=args[0], published=True)
    pprint(flows)

def workflow_translate(args: list):
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

def workflow_validate(args: list):
    if len(args) == 0:
        print('ERROR: no workflow configuration specified')
        return
    pprint(args)

    workflow_path = args[0]
    print(f"Workflow path: {workflow_path}")
    if not os.path.exists(workflow_path):
        print(f'ERROR: can not find workflow configuration {workflow_path}')
        return
    workflows = parse_workflow(workflow_path)
    pprint(workflows)
    gi = connect()
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
                inputs[input[0]] = { 'id': dsid, 'src':'hda'}

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
                inputs[input[0]] = {'id': dsid, 'src' : 'hda' }


def workflow_run(args:list):
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
                inputs[input[0]] = { 'id': dsid, 'src':'hda'}

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
                inputs[input[0]] = {'id': dsid, 'src' : 'hda' }

            invocation = gi.workflows.invoke_workflow(wfid, inputs=inputs, history_name=output_history_name)
            pprint(invocation)
            # output_path = os.path.join(INVOCATIONS_DIR, invocation['id'] + '.json')
            output_path = os.path.join(INVOCATIONS_DIR, output_history_name.replace(' ', '_') + '.json')
            with open(output_path, 'w') as f:
                json.dump(invocation, f, indent=4)
                print(f"Wrote {output_path}")


#
# Dataset related functions
#
def dataset_list(args: list):
    gi = connect()
    datasets = gi.datasets.get_datasets(limit=10000, offset=0) #, deleted=True, purged=True)
    if len(datasets) == 0:
        print('No datasets found')
        return
    print(f'Found {len(datasets)} datasets')
    for dataset in datasets:
        print(f"{dataset['id']}\t{dataset['name']}\t{dataset['deleted']}\t{dataset['purged']}")

def dataset_delete(args: list):
    print("dataset delete not implemented")

def dataset_upload(args: list):
    gi = connect()
    if len(args) == 0:
        print('ERROR: no dataset file given')
        return
    else:
        index = 1
        while index < len(args):
            arg = args[index]
            index += 1
            if arg == '-id':
                history = args[index]
                index += 1
            elif arg == '-c':
                history = gi.histories.create_history(args[index]).get('id')
                index += 1
            else:
                print('ERROR: invalid option')
    pprint(gi.tools.put_url(args[0], history))

def dataset_download(args: list):
    gi = connect()
    if len(args) == 0:
        print('ERROR: no workflow ID given')
        return
    elif len(args) > 1:
        pprint(gi.datasets.download_dataset(args[0], file_path=args[1]))
    else:
        pprint(gi.datasets.download_dataset(args[0]))

def dataset_show(args: list):  
    if len(args) == 0:
        print('ERROR: now dataset name given.')
        return
    gi = connect()
    datasets = gi.datasets.get_datasets(name=args[0])
    if len(datasets) == 0:
        print('WARNING: no datasets found with that name')
        return
    if len(datasets) > 1:
        print('WARNING: found more than one dataset with that name. Using the first')
        print('dataset in the list, which one that is will be indeterminate.')

    ds = datasets[0]
    pprint(ds)

def dataset_test(args: list):
    if len(args) == 0:
        print("ERROR: now dataset ID provided")
        return
    gi = connect()
    dataset = gi.datasets.show_dataset(args[0])
    if dataset is None:
        print(f"ERROR: no dataset with ID {args[0]}")
        return
    name = dataset['name']
    print(f"Found dataset with name {name}")
    print(yaml.dump(dataset))
    datasets = gi.datasets.get_datasets(name=name)
    if datasets is None or len(datasets) == 0:
        print(f"ERROR: could not find a dataset named {name}")
        return
    print(f"Found {len(datasets)} datasets")
    for dataset in datasets:
        print(f"{dataset['id']}\t{dataset['name']}")

#
# Library related functions
#

def library_list(args: list):
    print("library list not implemented")

def library_delete(args: list):
    print("library delete not implemented")

def library_upload(args: list):
    print("library upload not implemented")

def library_download(args: list):
    print("library download not implemented")

def library_show(args: list):
    print("library show not implemented")

#
# History related functions
#
def history_list(args:list):
    gi = connect()
    print('Listing histories')
    for history in gi.histories.get_histories():
        print(f"{history['id']}\t{history['name']}\t{history['deleted']}\t{history['published']}")

    print('Histories Published by all users')
    for history in gi.histories.get_published_histories():
        print(f"{history['id']}\t{history['name']}\t{history['deleted']}\t{history['published']}")

def history_download(args:list):
    print('history download not implemented')

def history_upload(args:list):
    print('history upload not implemented')

'''
workflow_commands = {
    'upload': workflow_upload,
    'download': workflow_download,
    'list': workflow_list,
    'delete': workflow_delete,
    'up': workflow_upload,
    'down': workflow_download,
    'dl': workflow_download,
    'ls': workflow_list,
    'rm': workflow_delete,
    'show': workflow_show,
    'help': workflow_help
}

library_commands = {
    'upload': library_upload,
    'download': library_download,
    'list': library_list,
    'delete': library_delete,
    'up': library_upload,
    'down': library_download,
    'dl': library_download,
    'ls': library_list,
    'rm': library_delete,
    'show': library_show,
    'help': library_help
}

dataset_commands = {
    'upload': dataset_upload,
    'download': dataset_download,
    'list': dataset_list,
    'delete': dataset_delete,
    'up': dataset_upload,
    'down': dataset_download,
    'dl': dataset_download,
    'ls': dataset_list,
    'rm': dataset_delete,
    'show': dataset_show,
    'help': dataset_help
}

all_commands = {
    'workflow': workflow_commands,
    'wf': workflow_commands,
    'dataset': dataset_commands,
    'ds': dataset_commands,
    'library': library_commands,
    'lib': library_commands
}
'''

all_commands = {}

def parse_profile(profile_name: str):
    profiles = None
    for profile_path in PROFILE_SEARCH_PATH:
        profile_path = os.path.expanduser(profile_path)
        # print(f'Checking profile {profile_path}')
        if os.path.exists(profile_path):
            with open(profile_path, 'r') as f:
                # print(f'Loading profile from {profile_path}')
                profiles = yaml.safe_load(f)
            break
    if profiles is None:
        print(f'ERROR: Could not locate an abm profile file in {PROFILE_SEARCH_PATH}')
        return False
    if profile_name not in profiles:
        print(f'ERROR: {profile_name} is not the name of a valid profile.')
        print(f'The defined profile names are {profiles.keys()}')
        return False
    global GALAXY_SERVER, API_KEY
    profile = profiles[profile_name]
    GALAXY_SERVER = profile['url']
    API_KEY = profile['key']
    return True

def get_menu(name: str):
    if name in all_commands:
        return all_commands[name]
    menu = dict()
    all_commands[name] = menu
    return menu

def register_handler(name:str, commands: list, handler):
    menu = get_menu(name)
    for command in commands:
        menu[command] = handler

def alias(shortcut, fullname):
    all_commands[shortcut] = all_commands[fullname]

def init_menu():
    register_handler("workflow", ['upload', 'up'], workflow_upload)
    register_handler("workflow", ['download', 'dl'], workflow_download)
    register_handler("workflow", ['list', 'ls'], workflow_list)
    register_handler("workflow", ['delete', 'del', 'rm'], workflow_delete)
    register_handler("workflow", ['run'], workflow_run)
    register_handler("workflow", ['show'], workflow_show)
    register_handler("workflow", ['translate', 'tr'], workflow_translate)
    register_handler("workflow", ['test'], workflow_test)
    register_handler("workflow", ['validate'], workflow_validate)
    register_handler("workflow", ['help', '-h'], workflow_help)
    register_handler("dataset", ['upload', 'up'], dataset_upload)
    register_handler("dataset", ['download', 'dl'], dataset_download)
    register_handler("dataset", ['list', 'ls'], dataset_list)
    register_handler("dataset", ['delete', 'del', 'rm'], dataset_delete)
    register_handler("dataset", ['show'], dataset_show)
    register_handler("dataset", ['test'], dataset_test)
    register_handler("dataset", ['help', '-h'], dataset_help)
    register_handler("history", ['list', 'ls'], history_list)
    register_handler("history", ['upload', 'up'], history_upload)
    register_handler("history", ['download', 'down', 'dl'], history_download)
    register_handler("history", ['help', '-h'], history_help)

    alias('wf', 'workflow')
    alias('ds', 'dataset')
    alias('hist', 'history')
    all_commands['wf'] = all_commands['workflow']
    all_commands['ds'] = all_commands['dataset']
    all_commands['hist'] = all_commands['history']


def parse_menu():
    menu_config = 'menu.yml'
    if not os.path.exists(menu_config):
        print("ERROR: Unable to load the menu configuration.")
        sys.exit(1)
    with open(menu_config) as f:
        menu_data = yaml.safe_load(f)
    for menu in menu_data:
        submenu = dict()
        for item in menu['menu']:
            for name in item['name']:
                submenu[name] = globals()[item['handler']]
        for name in menu['name']:
            all_commands[name] = submenu

def main():
    global API_KEY, GALAXY_SERVER
    value = os.environ.get('GALAXY_SERVER')
    if value is not None:
        GALAXY_SERVER = value

    value = os.environ.get('API_KEY')
    if value is not None:
        API_KEY = value

    commands = list()
    index = 1
    while index < len(sys.argv):
        arg = sys.argv[index]
        index += 1
        if arg in ['-k', '--key']:
            API_KEY = sys.argv[index]
            index += 1
        elif arg in ['-s', '--server']:
            GALAXY_SERVER = sys.argv[index]
            index += 1
        elif arg in ['-p', '--profile']:
            if not parse_profile(sys.argv[index]):
                return
            index += 1
        else:
            commands.append(arg)

    if len(commands) == 0:
        help()
        sys.exit(0)

    # parse_menu()
    init_menu()
    program = sys.argv[0]
    command = commands.pop(0)
    if command in ['-h', '--help', 'help']:
        help()
    elif command in ['-v', '--version', 'version']:
        print(f"    Galaxy Workflow Runner v{VERSION}")
        print(f"    Copyright 2021 The Galaxy Project. All Rights Reserved.")
    elif command in all_commands:
        if len(commands) == 0:
            print(f'ERROR: missing subcommand')
            print(f'Type ".{program} {command} help" for more help.')
            return

        subcommands = all_commands[command]
        subcommand = commands.pop(0)
        if subcommand not in subcommands:
            print(f'ERROR: unrecognized subcommand')
            print(f'Type ".{program} {command} help" for more help.')
            return
        # print(f'Dispatching "{command} {subcommand}"')
        handler = subcommands[subcommand]
        handler(commands)
    else:
        print(f'\n{bold("ERROR:")} Unknown command {bold("{command}")}')
        help()


if __name__ == '__main__':
    main()
    #parse_menu()

menu_yaml = '''
'''