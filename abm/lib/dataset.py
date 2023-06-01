import json

from common import connect, Context
from pprint import pprint
from pathlib import Path

import os
import yaml

def list(context: Context, args: list):
    gi = connect(context)
    kwargs = {
        'limit': 10000,
        'offset': 0
    }
    if len(args) > 0:
        if args[0] in ['-s', '--state']:
            if len(args) != 2:
                print("ERROR: Invalid command.")
                return
            kwargs['state'] = args[1]
        else:
            print(f"ERROR: Invalid parameter: {args[0]}")
            return
    #datasets = gi.datasets.get_datasets(limit=10000, offset=0)  # , deleted=True, purged=True)
    datasets = gi.datasets.get_datasets(**kwargs)
    if len(datasets) == 0:
        print('No datasets found')
        return
    print(f'Found {len(datasets)} datasets')
    print('ID\tHistory\tType\tDeleted\tState\tName')
    for dataset in datasets:
        state = dataset['state'] if 'state' in dataset else 'unknown'
        print(f"{dataset['id']}\t{dataset['history_id']}\t{dataset['history_content_type']}\t{dataset['deleted']}\t{state}\t{dataset['name']}")


def clean(context: Context, args: list):
    if len(args) == 0:
        invalid_states = ['error', 'discarded', 'unknown']
    else:
        invalid_states = args
    gi = connect(context)
    datasets = gi.datasets.get_datasets(limit=10000, offset=0)  # , deleted=True, purged=True)
    if len(datasets) == 0:
        print('No datasets found')
        return
    for dataset in datasets:
        state = dataset['state'] if 'state' in dataset else 'unknown'
        if not dataset['deleted'] and state in invalid_states:
            gi.histories.delete_dataset(dataset['history_id'], dataset['id'], True)
            print(f"Removed {dataset['id']}\t{state}\t{dataset['name']}")


def show(context: Context, args: list):
    if len(args) == 0:
        print("ERROR: no dataset ID provided")
        return
    gi = connect(context)
    result = gi.datasets.show_dataset(args[0])
    print(json.dumps(result, indent=4))


def get(context: Context, args: list):
    if len(args) == 0:
        print("ERROR: no dataset ID provided")
        return
    gi = connect(context)
    result = gi.datasets.get_datasets(args[0])
    print(json.dumps(result, indent=4))


def delete(context: Context, args: list):
    # gi = connect(context)
    print("dataset delete not implemented")


def upload(context: Context, args: list):
    history = None
    name = None
    url = None
    gi = None
    while len(args) > 0:
        arg = args.pop(0)
        if arg in ['--hs', '--hist', '--history']:
            history = args.pop(0)
        elif arg in ['-c', '--create']:
            gi = connect(context)
            history = gi.histories.create_history(args.pop(0)).get('id')
        elif arg in ['-n', '--name']:
            name = args.pop(0)
        elif url is not None:
            print(f'ERROR: invalid option. URL already set to {arg}')
            return
        else:
            url = arg
    if history is None:
        print("ERROR: please specify or create a history.")
        return
    if gi is None:
        gi = connect(context)
    if name:
        _import_from_url(gi, history, url, file_name=name)
    else:
        _import_from_url(gi, history, url)


def import_from_config(context: Context, args: list):
    gi = None
    key = None
    kwargs = {}
    while len(args) > 0:
        arg = args.pop(0)
        if arg in ['--hs', '--hist', '--history']:
            history = args.pop(0)
        elif arg in ['-c', '--create']:
            gi = connect(context)
            history = gi.histories.create_history(args.pop(0)).get('id')
        elif arg in ['-n', '--name']:
            kwargs['file_name'] = args.pop(0)
        elif key is not None:
            print(f"ERROR: key already set: {key}")
            return
        else:
            key = arg

    configfile = os.path.join(Path.home(), '.abm', 'datasets.yml')
    if not os.path.exists(configfile):
        print("ERROR: ABM has not been configured to import datasets.")
        print(f"Please create {configfile}")
        return

    with open(configfile, 'r') as f:
        datasets = yaml.safe_load(f)
    if not key in datasets:
        print(f"ERROR: dataset {key} has not been defined.")
        return
    url = datasets[key]

    if gi is None:
        gi = connect(context)
    response = gi.tools.put_url(url, history, **kwargs)
    print(json.dumps(response, indent=4))


def _import_from_url(gi, history, url, **kwargs):
    response = gi.tools.put_url(url, history, **kwargs)
    print(json.dumps(response, indent=4))


def download(context: Context, args: list):
    gi = connect(context)
    if len(args) == 0:
        print('ERROR: no dataset ID given')
        return
    elif len(args) > 1:
        pprint(gi.datasets.download_dataset(args[0], file_path=args[1]))
    else:
        pprint(gi.datasets.download_dataset(args[0]))


def find(context: Context, args: list):
    if len(args) == 0:
        print('ERROR: no dataset name given.')
        return
    gi = connect(context)
    datasets = gi.datasets.get_datasets(name=args[0])
    if len(datasets) == 0:
        print('WARNING: no datasets found with that name')
        return
    if len(datasets) > 1:
        print(f'WARNING: found {len(datasets)} datasets with that name.')

    for ds in datasets:
        pprint(ds)


def rename(context: Context, args: list):
    if len(args) != 3:
        print("ERROR: please provide the history ID, dataset ID, and new name.")
        return
    gi = connect(context)
    response = gi.histories.update_dataset(args[0], args[1], name=args[2])
    result = {
        'state': response['state'],
        'name': response['name']
    }
    print(json.dumps(result, indent=4))


def test(context: Context, args: list):
    if len(args) == 0:
        print("ERROR: no dataset ID provided")
        return
    gi = connect(context)
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
