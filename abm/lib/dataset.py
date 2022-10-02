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
    print('ID\tHistory\tDeleted\tState\tName')
    for dataset in datasets:
        state = dataset['state'] if 'state' in dataset else 'unknown'
        print(f"{dataset['id']}\t{dataset['history_id']}\t{dataset['deleted']}\t{state}\t{dataset['name']}")
        #pprint(dataset)


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
    pprint(gi.datasets.show_dataset(args[0]))


def delete(context: Context, args: list):
    # gi = connect(context)
    print("dataset delete not implemented")


def upload(context: Context, args: list):
    if len(args) != 3:
        print('ERROR: Invalid arguments.  Include the URL, and the ID of an existing history,')
        print('or the name of a history to be created.')
        return
    index = 1
    gi = None
    while index < len(args):
        arg = args[index]
        index += 1
        if arg == '-id':
            history = args[index]
            index += 1
        elif arg == '-c':
            gi = connect(context)
            history = gi.histories.create_history(args[index]).get('id')
            index += 1
        else:
            print(f'ERROR: invalid option {arg}')

    if gi is None:
        gi = connect(context)
    pprint(gi.tools.put_url(args[0], history))


def import_from_config(context: Context, args: list):
    if len(args) != 3:
        print('ERROR: Invalid arguments.  Include the dataset id, and the ID of an existing history,')
        print('or the name of a history to be created.')
        return

    gi = None
    if args[1] in ['-id', '--id']:
        history = args[2]
    elif args[1] in ['-c', '--create']:
        gi = connect(context)
        history = gi.histories.create_history(args[2]).get('id')
    else:
        print(f"Invalid option {args[1]}")
        return

    configfile = os.path.join(Path.home(), '.abm', 'datasets.yml')
    if not os.path.exists(configfile):
        print("ERROR: ABM has not been configured to import datasets.")
        print(f"Please create {configfile}")
        return

    key = args[0]
    with open(configfile, 'r') as f:
        datasets = yaml.safe_load(f)
    if not key in datasets:
        print(f"ERROR: dataset {key} has not been defined.")
        return
    url = datasets[key]

    if gi is None:
        gi = connect(context)
    pprint(gi.tools.put_url(url, history))


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
    result = gi.histories.update_dataset(args[0], args[1], name=args[2])
    pprint(result)


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
