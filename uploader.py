#!/usr/bin/env python3

"""
This script is loosely based on https://github.com/galaxyproject/bioblend/blob/main/docs/examples/run_imported_workflow.py

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
GALAXY_SERVER = 'https://benchmarking.usegvl.org/initial/galaxy/'

# Your Galaxy API key.  This can be specified in an environment variable or
# on the command line.
API_KEY = None


def bold(text):
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
    print (f"""
{bold('SYNOPSIS')}
    Upload workflows and dataset to a Galaxy instance.
    
{bold('USAGE')}
    ./uploader.py [library|dataset|workflow] COMMAND [OPTIONS]
    
{bold('COMMANDS')}

{bold('OPTIONS')}

{bold('EXAMPLES')}


Copyright 2021 The Galaxy Project. All rights reserved.    
""")

def workflow_help(args: list):
    print(f"""
    {bold('SYNOPSIS')}
        Manage workflows on a Galaxy instance.

    {bold('USAGE')}
        ./uploader.py workflow [list|show|delete|upload|download] [OPTIONS]

    {bold('COMMANDS')}
        
    {bold('OPTIONS')}

    {bold('EXAMPLES')}


    Copyright 2021 The Galaxy Project. All rights reserved.    
    """)


def library_help(args: list):
    print(f"""
    {bold('SYNOPSIS')}
        Manage dataset libraries on a Galaxy instance.

    {bold('USAGE')}
        ./uploader.py library [list|show|delete|upload] [OPTIONS]

    {bold('COMMANDS')}

    {bold('OPTIONS')}

    {bold('EXAMPLES')}


    Copyright 2021 The Galaxy Project. All rights reserved.    
    """)


def dataset_help(args: list):
    print(f"""
    {bold('SYNOPSIS')}
        Manage datasets on a Galaxy instance.

    {bold('USAGE')}
        ./uploader.py dataset [list|delete|upload|download] [OPTIONS]

    {bold('COMMANDS')}

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
    return bioblend.galaxy.GalaxyInstance(url=GALAXY_SERVER, key=API_KEY)


#
# Workflow related functions
#
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
    pprint(gi.workflows.export_workflow_dict(args[0]))

def workflow_show(args:list):
    if len(args) == 0:
        print('ERROR: no workflow ID given')
        return
    gi = connect()
    pprint(gi.workflows.show_workflow(args[0]))


#
# Dataset related functions
#
def dataset_list(args: list):
    gi = connect()
    datasets = gi.datasets.get_datasets(limit=100, deleted=False, purged=False)
    if len(datasets) == 0:
        print('No datasets found')
        return
    print(f'Found {len(datasets)} datasets')
    for dataset in datasets:
        print(f"{dataset['id']}\t{dataset['name']}")

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
    print("dataset show not implemented")

#
# Library related functions
#

def library_list(args: list):
    print("library list not implemented")

def library_delete(args: list):
    print("library delete not implemented")

def library_upload(args: list):
    print("library upload not implemented")

def library_show(args: list):
    print("library show not implemented")


workflow_commands = {
    'upload': workflow_upload,
    'download': workflow_download,
    'list': workflow_list,
    'delete': workflow_delete,
    'show': workflow_show,
    'help': workflow_help
}

library_commands = {
    'upload': library_upload,
    'list': library_list,
    'delete': library_delete,
    'show': library_show,
    'help': library_help
}

dataset_commands = {
    'upload': dataset_upload,
    'download': dataset_download,
    'list': dataset_list,
    'delete': dataset_delete,
    'show': dataset_show,
    'help': dataset_help
}

all_commands = {
    'workflow': workflow_commands,
    'dataset': dataset_commands,
    'library': library_commands
}


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
        else:
            commands.append(arg)

    if len(commands) == 0:
        help()
        sys.exit(0)
    command = commands.pop(0)
    if command in ['-h', '--help', 'help']:
        help()
    elif command in ['-v', '--version', 'version']:
        print(f"    Galaxy Workflow Runner v{VERSION}")
        print(f"    Copyright 2021 The Galaxy Project. All Rights Reserved.")
    elif command in all_commands:
        if len(commands) == 0:
            print(f'ERROR: missing subcommand')
            print(f'Type "./uploader.py {command} help" for more help.')
            return

        subcommands = all_commands[command]
        subcommand = commands.pop(0)
        if subcommand not in subcommands:
            print(f'ERROR: unrecognized subcommand')
            print(f'Type "./uploader.py {command} help" for more help.')
            return
        # print(f'Dispatching "{command} {subcommand}"')
        handler = subcommands[subcommand]
        handler(commands)
    else:
        print(f'\n{bold("ERROR:")} Unknown command {bold("{command}")}')
        help()


if __name__ == '__main__':
    main()

