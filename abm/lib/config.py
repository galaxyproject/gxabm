import argparse
import os

import yaml
from common import (
    Context,
    connect,
    find_config,
    get_yaml_parser,
    load_profiles,
    print_json,
    print_yaml,
    save_config,
    save_profiles,
)

# Import functions for bootstrap functionality
from . import dataset, history, workflow


def do_list(context: Context, args: list):
    profiles = load_profiles()
    print(f"Loaded {len(profiles)} profiles")
    for profile in profiles:
        print(f"{profile}\t{profiles[profile]['url']}")


def create(context: Context, argv: list):
    parser = argparse.ArgumentParser(prog='abm config create')
    parser.add_argument('profile_name', help='name of the profile to create')
    parser.add_argument('kube_path', nargs='?', help='path to kubeconfig file (backwards compatibility)')
    parser.add_argument('--url', help='Galaxy server URL')
    parser.add_argument('--key', help='Galaxy API key')
    parser.add_argument('--kube', help='path to kubeconfig file')

    args = parser.parse_args(argv)

    profiles = load_profiles()
    if args.profile_name in profiles:
        print("ERROR: a cloud configuration with that name already exists.")
        return

    # Handle backwards compatibility: if kube_path is provided as positional argument, use it
    kube_value = ""
    if args.kube_path:
        kube_value = args.kube_path
    elif args.kube:
        kube_value = args.kube

    profile = {"url": args.url or "", "key": args.key or "", "kube": kube_value}

    profiles[args.profile_name] = profile
    save_profiles(profiles)
    print_json(profile)


def remove(context: Context, args: list):
    if len(args) == 0:
        print("USAGE: abm config remove <cloud> [<cloud>...]")
        return
    profiles = load_profiles()
    for profile_name in args:
        if profile_name in profiles:
            del profiles[profile_name]
        else:
            print("ERROR: now cloud configuration with that name.")
    save_profiles(profiles)
    print_yaml(profiles)


def key(context: Context, args: list):
    if len(args) != 2:
        print(f"USAGE: abm config key <cloud> <key>")
        return
    profile_name = args[0]
    key = args[1]
    profiles = load_profiles()
    if not profile_name in profiles:
        print(f"ERROR: Unknown cloud {profile_name}")
        return
    profile = profiles[profile_name]
    profile["key"] = key
    save_profiles(profiles)
    print_json(profile)


def url(context: Context, args: list):
    if len(args) != 2:
        print(f"USAGE: abm config url <cloud> <url>")
        return
    profile_name = args[0]
    url = args[1]
    profiles = load_profiles()
    if not profile_name in profiles:
        print(f"ERROR: Unknown cloud {profile_name}")
        return
    profile = profiles[profile_name]
    profile["url"] = url
    save_profiles(profiles)
    print_json(profile)


def kube(context: Context, args: list):
    if len(args) != 2:
        print(f"USAGE: abm config kube <cloud> <kube_path>")
        return
    profile_name = args[0]
    kube_path = args[1]
    profiles = load_profiles()
    if not profile_name in profiles:
        print(f"ERROR: Unknown cloud {profile_name}")
        return
    profile = profiles[profile_name]
    profile["kube"] = kube_path
    save_profiles(profiles)
    print_json(profile)


def show(context: Context, args: list):
    if len(args) != 1:
        print("USAGE: abm config show <cloud>")
        return
    profiles = load_profiles()
    if args[0] not in profiles:
        print(f"ERROR: No such cloud {args[0]}")
        return
    print_json(profiles[args[0]])


def workflows(context: Context, args: list):
    # userfile = os.path.join(Path.home(), ".abm", "workflows.yml")
    userfile = find_config("workflows.yml")
    if userfile is None:
        print("ERROR: this instance has not been configured to import workflows.")
        return
    workflows = _load_config(userfile)
    if workflows is None:
        return
    save = False
    if len(args) == 0 or args[0] in ["list", "ls"]:
        print(f"Workflows defined in {userfile}")
        for key, url in workflows.items():
            print(f"{key:10} {url}")
    elif args[0] in ["delete", "del", "rm"]:
        if len(args) != 2:
            print("USAGE: abm config workflows delete <workflow>")
            return
        id = args[1]
        if id not in workflows:
            print(f"ERROR: No such workflow {id}")
            return
        url = workflows[id]
        del workflows[id]
        print(f"Removed workflow {id} -> {url}.")
        save = True
    elif args[0] in ["add", "new"]:
        if len(args) != 3:
            print("USAGE: abm config workflows add <workflow> <url>")
            return
        id = args[1]
        if id in workflows:
            print(f"ERROR: Workflow {id} already exists.")
            return
        url = args[2]
        workflows[id] = url
        print(f"Added workflow {id} -> {url}.")
        save = True
    else:
        print(f"ERROR: Unrecognized command {args[0]}")
    if save:
        save_config(userfile, workflows)


def datasets(context: Context, args: list):
    # userfile = os.path.join(Path.home(), ".abm", "datasets.yml")
    userfile = find_config("datasets.yml")
    if userfile is None:
        print("ERROR: this instance has not been configured to import datasets.")
        return
    datasets = _load_config(userfile)
    if datasets is None:
        return
    save = False
    if len(args) == 0 or args[0] in ["list", "ls"]:
        print(f"Datasets defined in {userfile}")
        for key, url in datasets.items():
            print(f"{key:10} {url}")
    elif args[0] in ["delete", "del", "rm"]:
        id = args[1]
        if id not in datasets:
            print(f"ERROR: No such dataset {id}")
            return
        url = datasets[id]
        del datasets[id]
        print(f"Removed dataset {id} -> {url}.")
        save = True
    elif args[0] in ["add", "new"]:
        if len(args) != 3:
            print("USAGE: abm config datasets add <dataset> <url>")
            return
        id = args[1]
        if id in datasets:
            print(f"ERROR: Dataset {id} already exists.")
            return
        url = args[2]
        datasets[id] = url
        print(f"Added dataset {id} -> {url}.")
        save = True
    else:
        print(f"ERROR: Unrecognized command {args[0]}")
    if save:
        save_config(userfile, datasets)


def histories(context: Context, args: list):
    userfile = find_config("histories.yml")
    if userfile is None:
        print("ERROR: this instance has not been configured to import histories.")
        return
    histories = _load_config(userfile)
    if histories is None:
        return
    save = False
    if len(args) == 0 or args[0] in ["list", "ls"]:
        print(f"Datasets defined in {userfile}")
        for key, url in histories.items():
            print(f"{key:10} {url}")
    elif args[0] in ["delete", "del", "rm"]:
        if len(args) != 2:
            print("USAGE: abm config histories delete <history>")
            return
        id = args[1]
        if id not in histories:
            print(f"ERROR: No such history {id}")
            return
        url = histories[id]
        del histories[id]
        save = True
        print(f"Removed history {id} -> {url}.")
    elif args[0] in ["add", "new"]:
        if len(args) != 3:
            print("USAGE: abm config histories add <history> <url>")
            return
        id = args[1]
        if id in histories:
            print(f"ERROR: History {id} already exists.")
            return
        url = args[2]
        histories[id] = url
        print(f"Added history {id} -> {url}.")
        save = True
    else:
        print(f"ERROR: Unrecognized command {args[0]}")
    if save:
        save_config(userfile, histories)


def _load_config(filepath):
    if not os.path.exists(filepath):
        print(f"ERROR: configuration file not found: {filepath}")
        return None
    with open(filepath, "r") as f:
        return yaml.safe_load(f)


def bootstrap(context: Context, args: list):
    """Configure a Galaxy instance by uploading datasets, histories, and workflows from a YAML configuration file."""
    if len(args) < 2:
        print("USAGE: abm config bootstrap <server> <config_file>")
        return

    server = args[0]
    config_file = args[1]

    # Create context for the specified server
    context = Context(server)

    if not os.path.exists(config_file):
        print(f"ERROR: configuration file not found: {config_file}")
        return

    # Load configuration file
    try:
        with open(config_file, 'r') as f:
            config = yaml.safe_load(f)
    except Exception as e:
        print(f"ERROR: failed to parse configuration file: {e}")
        return

    if config is None:
        print("ERROR: configuration file is empty")
        return

    # Process histories
    if 'histories' in config:
        histories = config['histories']
        print(f"Importing {len(histories)} histories...")
        for url in histories:
            try:
                # Call existing history import function
                history._import(context, [url])
            except Exception as e:
                print(f"ERROR: failed to import history from {url}: {e}")

    # Process datasets - support both simple list and grouped by history
    if 'datasets' in config:
        datasets = config['datasets']
        gi = connect(context)

        # Check if datasets is a simple list or dictionary
        if isinstance(datasets, list):
            # Simple list format - create default history
            print(f"Importing {len(datasets)} datasets into default history...")
            new_history = gi.histories.create_history(name="Configured Datasets")
            dataset_history = new_history['id']

            for url in datasets:
                try:
                    dataset._import_from_url(gi, dataset_history, url)
                except Exception as e:
                    print(f"ERROR: failed to import dataset from {url}: {e}")

        elif isinstance(datasets, dict):
            # Dictionary format - group by history name
            for history_name, urls in datasets.items():
                print(
                    f"Importing {len(urls)} datasets into history '{history_name}'..."
                )

                # Get or create the named history
                histories = gi.histories.get_histories(name=history_name)
                if histories:
                    dataset_history = histories[0]['id']
                else:
                    new_history = gi.histories.create_history(name=history_name)
                    dataset_history = new_history['id']

                for url in urls:
                    try:
                        dataset._import_from_url(gi, dataset_history, url)
                    except Exception as e:
                        print(f"ERROR: failed to import dataset from {url}: {e}")
        else:
            print("ERROR: datasets section must be either a list or dictionary")

    # Process workflows (with tool installation)
    if 'workflows' in config:
        workflows = config['workflows']
        print(f"Importing {len(workflows)} workflows (with tools)...")
        for url in workflows:
            try:
                # Call existing workflow import function with tools
                workflow.import_from_url(context, [url])
            except Exception as e:
                print(f"ERROR: failed to import workflow from {url}: {e}")

    # Process workflows (without tool installation)
    if 'workflows-no-tools' in config:
        workflows_no_tools = config['workflows-no-tools']
        print(f"Importing {len(workflows_no_tools)} workflows (without tools)...")
        for url in workflows_no_tools:
            try:
                # Call existing workflow import function without tools
                workflow.import_from_url(context, [url, '--no-tools'])
            except Exception as e:
                print(f"ERROR: failed to import workflow from {url}: {e}")

    print("Instance configuration complete!")
